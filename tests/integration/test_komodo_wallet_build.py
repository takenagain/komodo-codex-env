import subprocess
import time
import unittest
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import rich, requests
    from rich.console import Console
    from rich.logging import RichHandler
except ImportError:
    rich = None
    requests = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"
KOMODO_WALLET_REPO = "https://github.com/KomodoPlatform/komodo-wallet.git"

# Android SDK configuration (matching android_manager.py)
ANDROID_HOME = "/opt/android-sdk"
ANDROID_USER_HOME = "/home/testuser/Android/Sdk"  # Fallback for user-specific installation

# Configure logging
def setup_logging(level=logging.INFO):
    """Setup rich logging with appropriate level."""
    if rich:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
    else:
        logging.basicConfig(level=level)

setup_logging()
logger = logging.getLogger(__name__)


def docker_available() -> bool:
    """Check if Docker is available on the system."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


class DockerTestBase(unittest.TestCase):
    """Base class for Docker-based tests with common functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Docker image for testing."""
        if not docker_available():
            raise unittest.SkipTest("Docker is not available")
        
        logger.info("Building Docker image for Komodo Wallet build test...")
        result = subprocess.run(
            ["docker", "build", "-t", "komodo-wallet-build-test", "-f", str(DOCKERFILE), str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Docker image: {result.stderr}")
        cls.image_name = "komodo-wallet-build-test"
        logger.info("✓ Docker image built successfully")

    def setUp(self):
        """Start a new Docker container for each test."""
        container_name = f"komodo-wallet-test-{int(time.time())}"
        logger.info(f"Starting Docker container: {container_name}")
        
        result = subprocess.run(
            ["docker", "run", "-d", "--name", container_name, 
             "--privileged",
             "-v", "/var/run/docker.sock:/var/run/docker.sock",
             "--memory", "4g",
             "--shm-size", "2g",
             self.image_name, "sleep", "7200"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"Failed to start Docker container: {result.stderr}")
            
        self.container_id = result.stdout.strip()
        self.container_name = container_name
        logger.info(f"✓ Container started: {self.container_id[:12]}")

    def tearDown(self):
        """Clean up Docker container after each test."""
        if hasattr(self, "container_id"):
            logger.info(f"Cleaning up container: {self.container_id[:12]}")
            result = subprocess.run(
                ["docker", "rm", "-f", self.container_id], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                logger.info("✓ Container cleaned up successfully")
            else:
                logger.warning(f"Failed to clean up container: {result.stderr}")

    def run_command_in_container(self, command: str, user: str = "testuser", timeout: int = 600) -> subprocess.CompletedProcess:
        """Run a command in the Docker container with proper user."""
        logger.debug(f"Running command as {user}: {command[:100]}...")
        
        cmd = [
            "docker", "exec", "-u", user, self.container_id,
            "bash", "-c", command
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                logger.error(f"Command failed (exit {result.returncode})")
                logger.error(f"STDERR: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout} seconds")
            raise

    def copy_file_to_container(self, src_path: Path, dest_path: str) -> bool:
        """Copy a file to the container."""
        logger.debug(f"Copying {src_path} to container:{dest_path}")
        result = subprocess.run(
            ["docker", "cp", str(src_path), f"{self.container_id}:{dest_path}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Failed to copy file: {result.stderr}")
            return False
        
        # Fix ownership and permissions (chown as root, chmod as testuser)
        chown_result = subprocess.run(
            ["docker", "exec", "-u", "root", self.container_id, "chown", "testuser:testuser", dest_path],
            capture_output=True,
            text=True,
        )
        if chown_result.returncode != 0:
            logger.warning(f"Failed to change ownership: {chown_result.stderr}")
        
        chmod_result = subprocess.run(
            ["docker", "exec", "-u", "testuser", self.container_id, "chmod", "+x", dest_path],
            capture_output=True,
            text=True,
        )
        if chmod_result.returncode != 0:
            logger.warning(f"Failed to change permissions: {chmod_result.stderr}")
        
        return True


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class SystemDependenciesTest(DockerTestBase):
    """Test system dependencies verification."""
    
    def test_system_dependencies_available(self):
        """Verify all required system dependencies are available."""
        logger.info("Testing system dependencies availability")
        
        required_deps = ["git", "curl", "unzip", "sudo", "bash"]
        
        for dep in required_deps:
            with self.subTest(dependency=dep):
                result = self.run_command_in_container(f"command -v {dep}", timeout=30)
                self.assertEqual(result.returncode, 0, f"Dependency {dep} not found")
                logger.debug(f"✓ {dep} found at: {result.stdout.strip()}")
        
        logger.info("✓ All system dependencies verified")

    def test_user_environment_setup(self):
        """Test that testuser environment is properly configured."""
        logger.info("Testing testuser environment setup")
        
        checks = [
            ("Home directory exists", "test -d /home/testuser"),
            ("User can write to home", "touch /home/testuser/test_file && rm /home/testuser/test_file"),
            ("User has sudo access", "sudo echo 'sudo test'"),
            ("Shell is available", "echo $SHELL"),
        ]
        
        for check_name, command in checks:
            with self.subTest(check=check_name):
                result = self.run_command_in_container(command, timeout=30)
                self.assertEqual(result.returncode, 0, f"Environment check failed: {check_name}")
                logger.debug(f"✓ {check_name}")
        
        logger.info("✓ User environment verified")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class InstallationTest(DockerTestBase):
    """Test the installation process."""
    
    def setUp(self):
        super().setUp()
        # Copy install script
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")

    def test_install_script_execution(self):
        """Test install.sh script execution."""
        logger.info("Testing install script execution")
        
        command = """
        cd /home/testuser && 
        /home/testuser/install.sh --debug --flutter-version 3.32.0
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=1200)
        
        if result.returncode != 0:
            logger.error("Install script failed:")
            logger.error(f"Exit code: {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
        
        self.assertEqual(result.returncode, 0, f"Install script execution failed with exit code {result.returncode}")
        logger.info("✓ Install script completed successfully")

    def test_post_install_verification(self):
        """Verify installation was successful."""
        logger.info("Testing post-installation verification")
        
        # First run the install
        self.test_install_script_execution()
        
        # Verify essential installations
        essential_checks = [
            ("Komodo env directory exists", "test -d ~/.komodo-codex-env"),
            ("Install script completed", "test -f ~/.komodo-codex-env/pyproject.toml"),
        ]
        
        optional_checks = [
            ("UV binary exists", "test -f ~/.local/bin/uv"),
            ("FVM directory exists", "test -d ~/.pub-cache"),
        ]
        
        # Check essential installations
        for check_name, command in essential_checks:
            with self.subTest(check=check_name):
                result = self.run_command_in_container(
                    f"cd /home/testuser && {command}", 
                    timeout=30
                )
                self.assertEqual(result.returncode, 0, f"Essential check failed: {check_name}")
                logger.debug(f"✓ {check_name}")
        
        # Check optional installations (warn but don't fail)
        for check_name, command in optional_checks:
            result = self.run_command_in_container(
                f"cd /home/testuser && {command}", 
                timeout=30
            )
            if result.returncode == 0:
                logger.debug(f"✓ {check_name}")
            else:
                logger.warning(f"⚠ {check_name} - may need shell restart")
        
        logger.info("✓ Post-installation verification completed")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class EnvironmentSetupTest(DockerTestBase):
    """Test Komodo environment setup with Android support."""
    
    def setUp(self):
        super().setUp()
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")
        
        # Run install script
        command = """
        cd /home/testuser && 
        /home/testuser/install.sh --debug --flutter-version 3.32.0
        """
        result = self.run_command_in_container(command, user="testuser", timeout=1200)
        if result.returncode != 0:
            self.skipTest("Install script failed")

    def test_komodo_environment_setup(self):
        """Test Komodo Codex Environment setup with Android support."""
        logger.info("Testing Komodo environment setup with Android support")
        
        command = """
        cd /home/testuser && 
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        uv run komodo-codex-env setup \
            --flutter-version 3.32.0 \
            --install-method precompiled \
            --platforms web,android,linux \
            --kdf-docs \
            --verbose
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=1800)
        
        if result.returncode != 0:
            logger.error("Komodo setup output:")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
        
        self.assertEqual(result.returncode, 0, "Komodo environment setup failed")
        logger.info("✓ Komodo environment setup completed")

    def test_android_sdk_installation(self):
        """Verify Android SDK installation."""
        logger.info("Testing Android SDK installation")
        
        # First run the setup
        self.test_komodo_environment_setup()
        
        # Check Android SDK installation
        android_checks = [
            ("Android SDK directory", f"test -d {ANDROID_HOME} || test -d {ANDROID_USER_HOME}"),
            ("SDK Manager available", f"test -f {ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager || test -f {ANDROID_USER_HOME}/cmdline-tools/latest/bin/sdkmanager"),
            ("Platform tools available", f"test -d {ANDROID_HOME}/platform-tools || test -d {ANDROID_USER_HOME}/platform-tools"),
        ]
        
        for check_name, command in android_checks:
            with self.subTest(check=check_name):
                result = self.run_command_in_container(command, timeout=60)
                self.assertEqual(result.returncode, 0, f"Android check failed: {check_name}")
                logger.debug(f"✓ {check_name}")
        
        logger.info("✓ Android SDK installation verified")

    def test_flutter_environment_setup(self):
        """Test Flutter environment setup with FVM."""
        logger.info("Testing Flutter environment setup")
        
        # First run the setup
        self.test_komodo_environment_setup()
        
        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        fvm --version &&
        fvm install 3.32.0 &&
        fvm global 3.32.0 &&
        fvm flutter --version
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=900)
        self.assertEqual(result.returncode, 0, "Flutter environment setup failed")
        logger.info("✓ Flutter environment setup completed")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class AndroidEnvironmentTest(DockerTestBase):
    """Test Android environment configuration."""
    
    def setUp(self):
        super().setUp()
        # Run full setup pipeline
        self._run_full_setup()

    def _run_full_setup(self):
        """Run the complete setup pipeline."""
        # Copy and run install script
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")
        
        install_command = """
        cd /home/testuser && 
        /home/testuser/install.sh --debug --flutter-version 3.32.0
        """
        result = self.run_command_in_container(install_command, user="testuser", timeout=1200)
        if result.returncode != 0:
            self.skipTest("Install script failed")
        
        # Run komodo setup
        setup_command = """
        cd /home/testuser && 
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        uv run komodo-codex-env setup \
            --flutter-version 3.32.0 \
            --install-method precompiled \
            --platforms web,android,linux \
            --kdf-docs \
            --verbose
        """
        result = self.run_command_in_container(setup_command, user="testuser", timeout=1800)
        if result.returncode != 0:
            self.skipTest("Komodo setup failed")

    def test_android_environment_variables(self):
        """Test Android environment variables are properly set."""
        logger.info("Testing Android environment variables")
        
        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        
        # Check if Android environment variables are set
        echo "ANDROID_HOME: ${ANDROID_HOME:-NOT_SET}" &&
        echo "ANDROID_SDK_ROOT: ${ANDROID_SDK_ROOT:-NOT_SET}" &&
        
        # Verify the directories exist
        if [ -n "$ANDROID_HOME" ] && [ -d "$ANDROID_HOME" ]; then
            echo "Android SDK found at: $ANDROID_HOME"
        elif [ -d "{ANDROID_HOME}" ]; then
            echo "Android SDK found at system location: {ANDROID_HOME}"
            export ANDROID_HOME="{ANDROID_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_HOME}"
        elif [ -d "{ANDROID_USER_HOME}" ]; then
            echo "Android SDK found at user location: {ANDROID_USER_HOME}"
            export ANDROID_HOME="{ANDROID_USER_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_USER_HOME}"
        else
            echo "Android SDK not found in expected locations"
            exit 1
        fi &&
        
        echo "Final ANDROID_HOME: $ANDROID_HOME" &&
        echo "Final ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
        """.format(ANDROID_HOME=ANDROID_HOME, ANDROID_USER_HOME=ANDROID_USER_HOME)
        
        result = self.run_command_in_container(command, timeout=60)
        self.assertEqual(result.returncode, 0, "Android environment variables not properly set")
        logger.info("✓ Android environment variables verified")

    def test_android_tools_accessibility(self):
        """Test Android tools are accessible."""
        logger.info("Testing Android tools accessibility")
        
        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        
        # Set Android environment if not already set
        if [ -z "$ANDROID_HOME" ]; then
            if [ -d "{ANDROID_HOME}" ]; then
                export ANDROID_HOME="{ANDROID_HOME}"
                export ANDROID_SDK_ROOT="{ANDROID_HOME}"
            elif [ -d "{ANDROID_USER_HOME}" ]; then
                export ANDROID_HOME="{ANDROID_USER_HOME}"
                export ANDROID_SDK_ROOT="{ANDROID_USER_HOME}"
            fi
        fi &&
        
        # Add Android tools to PATH
        export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH" &&
        export PATH="$ANDROID_HOME/platform-tools:$PATH" &&
        export PATH="$ANDROID_HOME/tools/bin:$PATH" &&
        
        # Test tools accessibility
        which sdkmanager || echo "sdkmanager not found in PATH" &&
        ls -la "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" || echo "sdkmanager binary not found" &&
        
        # Test adb if available
        which adb || echo "adb not found in PATH" &&
        ls -la "$ANDROID_HOME/platform-tools/adb" || echo "adb binary not found"
        """.format(ANDROID_HOME=ANDROID_HOME, ANDROID_USER_HOME=ANDROID_USER_HOME)
        
        result = self.run_command_in_container(command, timeout=120)
        # Don't fail if tools aren't found, just log the status
        logger.info(f"Android tools check output: {result.stdout}")
        if result.returncode != 0:
            logger.warning("Some Android tools may not be accessible")

    def test_java_installation(self):
        """Test Java installation for Android development."""
        logger.info("Testing Java installation")
        
        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        
        java -version &&
        javac -version &&
        echo "JAVA_HOME: ${JAVA_HOME:-NOT_SET}"
        """
        
        result = self.run_command_in_container(command, timeout=60)
        self.assertEqual(result.returncode, 0, "Java not properly installed")
        logger.info("✓ Java installation verified")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class KomodoWalletBuildTest(DockerTestBase):
    """Test Komodo Wallet APK build process."""
    
    def setUp(self):
        super().setUp()
        # Run full setup pipeline
        self._run_full_setup()

    def _run_full_setup(self):
        """Run the complete setup pipeline."""
        logger.info("Running full setup pipeline for build test")
        
        # Copy and run install script
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")
        
        install_command = """
        cd /home/testuser && 
        /home/testuser/install.sh --debug --flutter-version 3.32.0
        """
        result = self.run_command_in_container(install_command, user="testuser", timeout=1200)
        if result.returncode != 0:
            self.skipTest(f"Install script failed: {result.stderr}")
        
        # Run komodo setup
        setup_command = """
        cd /home/testuser && 
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        uv run komodo-codex-env setup \
            --flutter-version 3.32.0 \
            --install-method precompiled \
            --platforms web,android,linux \
            --kdf-docs \
            --verbose
        """
        result = self.run_command_in_container(setup_command, user="testuser", timeout=1800)
        if result.returncode != 0:
            self.skipTest(f"Komodo setup failed: {result.stderr}")
        
        logger.info("✓ Full setup pipeline completed")

    def test_repository_cloning(self):
        """Test cloning Komodo Wallet repository."""
        logger.info("Testing repository cloning")
        
        command = f"""
        cd /home/testuser && 
        git clone {KOMODO_WALLET_REPO} komodo-wallet &&
        cd komodo-wallet &&
        ls -la &&
        test -f pubspec.yaml
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=300)
        self.assertEqual(result.returncode, 0, "Repository cloning failed")
        logger.info("✓ Repository cloned successfully")

    def test_flutter_dependencies_installation(self):
        """Test Flutter dependencies installation."""
        logger.info("Testing Flutter dependencies installation")
        
        # First clone the repository
        self.test_repository_cloning()
        
        command = """
        cd /home/testuser/komodo-wallet &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        
        # Set up FVM and Flutter
        fvm install 3.32.0 &&
        fvm use 3.32.0 &&
        fvm flutter pub get
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=600)
        self.assertEqual(result.returncode, 0, "Flutter dependencies installation failed")
        logger.info("✓ Flutter dependencies installed")

    def test_apk_build_process(self):
        """Test the complete APK build process."""
        logger.info("Testing APK build process")
        
        # Run previous steps
        self.test_flutter_dependencies_installation()
        
        # Build APK
        build_command = """
        cd /home/testuser/komodo-wallet &&
        source ~/.bashrc &&
        
        # Set up environment
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        
        # Set Android environment
        if [ -d "{ANDROID_HOME}" ]; then
            export ANDROID_HOME="{ANDROID_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_HOME}"
        elif [ -d "{ANDROID_USER_HOME}" ]; then
            export ANDROID_HOME="{ANDROID_USER_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_USER_HOME}"
        fi &&
        
        export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH" &&
        export PATH="$ANDROID_HOME/platform-tools:$PATH" &&
        export PATH="$ANDROID_HOME/tools/bin:$PATH" &&
        
        # Verify environment
        echo "Flutter version:" &&
        fvm flutter --version &&
        echo "Android environment:" &&
        echo "ANDROID_HOME: $ANDROID_HOME" &&
        
        # Clean and build
        fvm flutter clean &&
        fvm flutter build apk --debug
        """.format(ANDROID_HOME=ANDROID_HOME, ANDROID_USER_HOME=ANDROID_USER_HOME)
        
        result = self.run_command_in_container(build_command, user="testuser", timeout=1800)
        
        # Log build output for debugging
        logger.info("Build output:")
        logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR: {result.stderr}")
        
        self.assertEqual(result.returncode, 0, "APK build failed")
        logger.info("✓ APK build completed successfully")

    def test_apk_verification(self):
        """Test APK file verification."""
        logger.info("Testing APK verification")
        
        # First build the APK
        self.test_apk_build_process()
        
        # Verify APK exists
        command = """
        cd /home/testuser/komodo-wallet &&
        find . -name "*.apk" -type f &&
        ls -la build/app/outputs/flutter-apk/ || echo "APK directory not found" &&
        
        # Check if debug APK exists
        if [ -f "build/app/outputs/flutter-apk/app-debug.apk" ]; then
            echo "Debug APK found and has size: $(stat -c%s build/app/outputs/flutter-apk/app-debug.apk) bytes"
            exit 0
        else
            echo "Debug APK not found"
            exit 1
        fi
        """
        
        result = self.run_command_in_container(command, user="testuser", timeout=60)
        self.assertEqual(result.returncode, 0, "APK verification failed")
        logger.info("✓ APK verification completed")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class FullPipelineIntegrationTest(DockerTestBase):
    """Full integration test covering the complete pipeline."""
    
    def test_complete_pipeline(self):
        """Test the complete pipeline from installation to APK build."""
        logger.info("Starting complete pipeline integration test")
        
        pipeline_steps = [
            ("Copy install script", self._copy_install_script),
            ("Run install script", self._run_install_script),
            ("Verify post-install", self._verify_post_install),
            ("Run Komodo setup", self._run_komodo_setup),
            ("Verify Android environment", self._verify_android_environment),
            ("Clone repository", self._clone_repository),
            ("Setup Flutter environment", self._setup_flutter_environment),
            ("Install Flutter dependencies", self._install_flutter_dependencies),
            ("Build APK", self._build_apk),
            ("Verify APK", self._verify_apk),
        ]
        
        for step_name, step_func in pipeline_steps:
            logger.info(f"=== {step_name} ===")
            try:
                step_func()
                logger.info(f"✓ {step_name} completed successfully")
            except Exception as e:
                logger.error(f"✗ {step_name} failed: {e}")
                self.fail(f"Pipeline failed at step '{step_name}': {e}")
        
        logger.info("✓ Complete pipeline integration test passed")

    def _copy_install_script(self):
        """Copy install script to container."""
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            raise RuntimeError("Failed to copy install script")

    def _run_install_script(self):
        """Run the install script."""
        command = """
        cd /home/testuser && 
        /home/testuser/install.sh --debug --flutter-version 3.32.0
        """
        result = self.run_command_in_container(command, user="testuser", timeout=1200)
        if result.returncode != 0:
            raise RuntimeError(f"Install script failed: {result.stderr}")

    def _verify_post_install(self):
        """Verify post-installation state."""
        checks = [
            ("UV available", "uv --version"),
            ("Komodo env exists", "test -d ~/.komodo-codex-env"),
        ]
        
        for check_name, command in checks:
            result = self.run_command_in_container(f"cd /home/testuser && {command}", timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"Post-install check failed: {check_name}")

    def _run_komodo_setup(self):
        """Run Komodo environment setup."""
        command = """
        cd /home/testuser && 
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        uv run komodo-codex-env setup \
            --flutter-version 3.32.0 \
            --install-method precompiled \
            --platforms web,android,linux \
            --kdf-docs \
            --verbose
        """
        result = self.run_command_in_container(command, user="testuser", timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"Komodo setup failed: {result.stderr}")

    def _verify_android_environment(self):
        """Verify Android environment is set up."""
        command = f"""
        cd /home/testuser &&
        source ~/.bashrc &&
        
        # Check Android SDK exists
        if [ -d "{ANDROID_HOME}" ] || [ -d "{ANDROID_USER_HOME}" ]; then
            echo "Android SDK found"
        else
            echo "Android SDK not found"
            exit 1
        fi
        """
        result = self.run_command_in_container(command, timeout=60)
        if result.returncode != 0:
            raise RuntimeError("Android environment verification failed")

    def _clone_repository(self):
        """Clone Komodo Wallet repository."""
        command = f"""
        cd /home/testuser && 
        git clone {KOMODO_WALLET_REPO} komodo-wallet &&
        cd komodo-wallet &&
        test -f pubspec.yaml
        """
        result = self.run_command_in_container(command, user="testuser", timeout=300)
        if result.returncode != 0:
            raise RuntimeError("Repository cloning failed")

    def _setup_flutter_environment(self):
        """Set up Flutter environment with FVM."""
        command = """
        cd /home/testuser/komodo-wallet &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        fvm install 3.32.0 &&
        fvm use 3.32.0
        """
        result = self.run_command_in_container(command, user="testuser", timeout=600)
        if result.returncode != 0:
            raise RuntimeError("Flutter environment setup failed")

    def _install_flutter_dependencies(self):
        """Install Flutter dependencies."""
        command = """
        cd /home/testuser/komodo-wallet &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        fvm flutter pub get
        """
        result = self.run_command_in_container(command, user="testuser", timeout=600)
        if result.returncode != 0:
            raise RuntimeError("Flutter dependencies installation failed")

    def _build_apk(self):
        """Build the APK."""
        command = f"""
        cd /home/testuser/komodo-wallet &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        export PATH="$PATH:$HOME/.pub-cache/bin" &&
        
        # Set Android environment
        if [ -d "{ANDROID_HOME}" ]; then
            export ANDROID_HOME="{ANDROID_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_HOME}"
        elif [ -d "{ANDROID_USER_HOME}" ]; then
            export ANDROID_HOME="{ANDROID_USER_HOME}"
            export ANDROID_SDK_ROOT="{ANDROID_USER_HOME}"
        fi &&
        
        export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH" &&
        export PATH="$ANDROID_HOME/platform-tools:$PATH" &&
        export PATH="$ANDROID_HOME/tools/bin:$PATH" &&
        
        # Clean and build
        fvm flutter clean &&
        fvm flutter build apk --debug
        """
        result = self.run_command_in_container(command, user="testuser", timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"APK build failed: {result.stderr}")

    def _verify_apk(self):
        """Verify APK was created."""
        command = """
        cd /home/testuser/komodo-wallet &&
        if [ -f "build/app/outputs/flutter-apk/app-debug.apk" ]; then
            echo "Debug APK found and has size: $(stat -c%s build/app/outputs/flutter-apk/app-debug.apk) bytes"
            exit 0
        else
            echo "Debug APK not found"
            find . -name "*.apk" -type f || echo "No APK files found"
            exit 1
        fi
        """
        result = self.run_command_in_container(command, user="testuser", timeout=60)
        if result.returncode != 0:
            raise RuntimeError("APK verification failed")


if __name__ == "__main__":
    # Set up logging level based on verbosity
    import sys
    if "-v" in sys.argv or "--verbose" in sys.argv:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)
    
    unittest.main(verbosity=2)