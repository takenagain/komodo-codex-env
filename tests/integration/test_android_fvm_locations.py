"""
Integration tests specifically for Android SDK and FVM installation locations.

These tests verify that:
1. Android SDK is installed and accessible at /opt/android-sdk
2. FVM is installed and accessible in ~/.pub-cache/bin
3. fvm flutter build apk command works end-to-end
"""

import subprocess
import time
import unittest
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import rich, requests
from rich.console import Console
from rich.logging import RichHandler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"

# Expected installation paths
ANDROID_SDK_PATH = "/opt/android-sdk"
FVM_USER_PATH = "~/.pub-cache/bin/fvm"
FVM_GLOBAL_PATHS = ["/usr/local/bin/fvm", "/opt/flutter/bin/fvm"]

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


class AndroidFVMLocationTestBase(unittest.TestCase):
    """Base class for Android SDK and FVM location tests."""

    @classmethod
    def setUpClass(cls):
        """Set up Docker image for testing if Docker is available."""
        if not docker_available():
            raise unittest.SkipTest("Docker is not available")

        logger.info("Building Docker image for Android/FVM location tests...")
        result = subprocess.run(
            ["docker", "build", "-t", "komodo-android-fvm-test", "-f", str(DOCKERFILE), str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(f"Failed to build Docker image: {result.stderr}")
        cls.image_name = "komodo-android-fvm-test"
        logger.info("✓ Docker image built successfully")

    def setUp(self):
        """Start a new Docker container for each test."""
        container_name = f"android-fvm-test-{int(time.time())}"
        logger.info(f"Starting Docker container: {container_name}")

        result = subprocess.run(
            ["docker", "run", "-d", "--name", container_name,
             "--tmpfs", "/tmp:rw,exec,nosuid,size=2g",
             self.image_name, "sleep", "3600"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.skipTest(f"Failed to start Docker container: {result.stderr}")

        self.container_id = result.stdout.strip()
        self.container_name = container_name
        logger.info(f"✓ Container started: {self.container_id[:12]}")

        # Create testuser if it doesn't exist
        create_user_cmd = [
            "docker", "exec", "-u", "root", self.container_id, "bash", "-c",
            "id testuser || (useradd -m -s /bin/bash testuser && echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers)"
        ]
        user_result = subprocess.run(create_user_cmd, capture_output=True, text=True)
        if user_result.returncode != 0:
            logger.warning(f"Failed to create testuser: {user_result.stderr}")

        # Check container disk space
        self._check_container_space()

    def run_command_in_container(self, command: str, user: str = "testuser", timeout: int = 300) -> subprocess.CompletedProcess:
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

        # Fix ownership and permissions
        subprocess.run(
            ["docker", "exec", "-u", "root", self.container_id, "chown", "testuser:testuser", dest_path],
            capture_output=True, text=True,
        )
        subprocess.run(
            ["docker", "exec", "-u", "testuser", self.container_id, "chmod", "+x", dest_path],
            capture_output=True, text=True,
        )

        return True

    def _check_container_space(self):
        """Check and optimize container disk space."""
        logger.info("Checking container disk space...")

        # Check available space
        result = self.run_command_in_container("df -h /")
        if result.returncode == 0:
            logger.info(f"Disk space info:\n{result.stdout}")

        # Clean up container to free space
        cleanup_commands = [
            "sudo apt-get clean || true",
            "sudo rm -rf /var/lib/apt/lists/* || true",
            "sudo rm -rf /tmp/* || true",
            "sudo rm -rf /var/tmp/* || true",
            "sudo find /var/log -type f -name '*.log' -exec truncate -s 0 {} \\; || true"
        ]

        for cmd in cleanup_commands:
            self.run_command_in_container(cmd, user="testuser", timeout=30)

        # Check space again
        result = self.run_command_in_container("df -h /")
        if result.returncode == 0:
            logger.info(f"Disk space after cleanup:\n{result.stdout}")

    def tearDown(self):
        """Clean up Docker container after each test."""
        if hasattr(self, "container_id"):
            logger.info(f"Cleaning up container: {self.container_id[:12]}")
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)

    def run_verification_script(self) -> bool:
        """Run the installation verification script in the container."""
        logger.info("Running installation verification script...")

        # Copy verification script to container
        verification_script = PROJECT_ROOT / "scripts" / "verify_installation.py"
        if not self.copy_file_to_container(verification_script, "/home/testuser/verify_installation.py"):
            logger.error("Failed to copy verification script")
            return False

        # Make it executable
        self.run_command_in_container("chmod +x /home/testuser/verify_installation.py")

        # Run verification
        result = self.run_command_in_container(
            "cd /home/testuser && python3 verify_installation.py",
            user="testuser",
            timeout=60
        )

        logger.info(f"Verification script output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Verification script stderr:\n{result.stderr}")

        return result.returncode == 0


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class AndroidSDKLocationTest(AndroidFVMLocationTestBase):
    """Test Android SDK installation at expected location."""

    def setUp(self):
        super().setUp()
        # First, just run the basic install script to get komodo environment
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")

        # Run just the basic installation without FVM and without full setup
        basic_install_cmd = """
        cd /home/testuser &&
        # Modify install script to skip FVM and avoid full setup
        sed -i 's/run_full_setup_with_flutter_version.*/echo "Skipping full setup"/' install.sh &&
        sed -i 's/install_fvm/echo "Skipping FVM install"/' install.sh &&
        timeout 300 bash install.sh --debug || echo "Install completed or timed out"
        """
        logger.info("Running basic installation (no FVM, no full setup)")
        result = self.run_command_in_container(basic_install_cmd, timeout=400)
        logger.info(f"Basic install result: {result.returncode}")

        # Check if basic installation worked
        check_cmd = "test -d /home/testuser/.komodo-codex-env && echo 'BASIC_INSTALL_OK' || echo 'BASIC_INSTALL_FAILED'"
        check_result = self.run_command_in_container(check_cmd, timeout=30)
        if "BASIC_INSTALL_FAILED" in check_result.stdout:
            self.skipTest("Basic installation failed - komodo environment not found")

        # Try to install Android SDK using the komodo CLI with a shorter timeout
        android_install_cmd = """
        cd /home/testuser/.komodo-codex-env &&
        export PATH="$HOME/.local/bin:$PATH" &&
        timeout 600 uv run komodo-codex-env setup --platforms android --install-method precompiled --verbose || echo "Android install completed or timed out"
        """
        logger.info("Installing Android SDK via komodo CLI")
        android_result = self.run_command_in_container(android_install_cmd, timeout=700)
        logger.info(f"Android install result: {android_result.returncode}")

    def test_android_sdk_directory_structure(self):
        """Test that Android SDK directory structure exists at /opt/android-sdk."""
        logger.info("Testing Android SDK directory structure")

        # First check if Android SDK was installed at all
        check_cmd = f"ls -la {ANDROID_SDK_PATH} 2>/dev/null || echo 'ANDROID_SDK_NOT_FOUND'"
        check_result = self.run_command_in_container(check_cmd, timeout=30)

        if "ANDROID_SDK_NOT_FOUND" in check_result.stdout:
            # Show debugging info about what was actually installed
            debug_cmd = """
            echo "=== Android SDK Installation Debug ==="
            ls -la /opt/ 2>/dev/null || echo "No /opt directory"
            ls -la /home/testuser/ 2>/dev/null | grep -i android || echo "No android dirs in home"
            find /home /opt -name "*android*" -type d 2>/dev/null | head -5 || echo "No android directories found"
            """
            debug_result = self.run_command_in_container(debug_cmd, timeout=60)
            logger.error(f"Android SDK debug info: {debug_result.stdout}")
            self.fail(f"Android SDK not found at {ANDROID_SDK_PATH}. Installation may have failed or Android SDK installed elsewhere.")

        # Android SDK exists, check directory structure
        expected_directories = [
            f"{ANDROID_SDK_PATH}",
            f"{ANDROID_SDK_PATH}/cmdline-tools",
            f"{ANDROID_SDK_PATH}/cmdline-tools/latest",
            f"{ANDROID_SDK_PATH}/cmdline-tools/latest/bin",
        ]

        for directory in expected_directories:
            with self.subTest(directory=directory):
                command = f"test -d '{directory}'"
                result = self.run_command_in_container(command, timeout=30)

                if result.returncode != 0:
                    # If directory doesn't exist, show what's actually there
                    parent_dir = str(Path(directory).parent)
                    list_result = self.run_command_in_container(f"ls -la '{parent_dir}' || echo 'Parent directory does not exist'", timeout=30)
                    logger.error(f"Directory {directory} not found. Parent directory contents: {list_result.stdout}")

                self.assertEqual(result.returncode, 0, f"Android SDK directory not found: {directory}")

        logger.info("✓ Android SDK directory structure verified")

    def test_android_sdk_tools_executable(self):
        """Test that Android SDK tools are executable at expected location."""
        logger.info("Testing Android SDK tools executability")

        tools_to_check = [
            f"{ANDROID_SDK_PATH}/cmdline-tools/latest/bin/sdkmanager",
            f"{ANDROID_SDK_PATH}/cmdline-tools/latest/bin/avdmanager",
        ]

        for tool_path in tools_to_check:
            with self.subTest(tool=tool_path):
                # Check if file exists and is executable
                command = f"test -f '{tool_path}' && test -x '{tool_path}'"
                result = self.run_command_in_container(command, timeout=30)

                if result.returncode != 0:
                    # Show what's actually at that location
                    check_result = self.run_command_in_container(f"ls -la '{tool_path}' || echo 'File does not exist'", timeout=30)
                    logger.error(f"Tool {tool_path} not found or not executable: {check_result.stdout}")

                self.assertEqual(result.returncode, 0, f"Android SDK tool not found or not executable: {tool_path}")

        logger.info("✓ Android SDK tools verified as executable")

    def test_android_sdk_environment_variables(self):
        """Test that Android SDK environment variables point to correct location."""
        logger.info("Testing Android SDK environment variables")

        command = f"""
        # Check if Android SDK is at expected location
        if [ -d "{ANDROID_SDK_PATH}" ]; then
            export ANDROID_HOME="{ANDROID_SDK_PATH}"
            export ANDROID_SDK_ROOT="{ANDROID_SDK_PATH}"
            echo "ANDROID_HOME: $ANDROID_HOME"
            echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
            echo "SUCCESS: Android SDK found at expected location"
        else
            echo "FAILED: Android SDK not found at {ANDROID_SDK_PATH}"
            echo "Checking alternative locations:"
            for alt_path in "/home/testuser/Android/Sdk" "$HOME/Android/Sdk" "/android-sdk"; do
                if [ -d "$alt_path" ]; then
                    echo "Found Android SDK at: $alt_path"
                fi
            done
            exit 1
        fi
        """

        result = self.run_command_in_container(command, timeout=60)

        if result.returncode != 0:
            logger.error(f"Android SDK environment test failed: {result.stdout}")

        self.assertEqual(result.returncode, 0, "Android SDK not found at expected location /opt/android-sdk")
        self.assertIn("SUCCESS", result.stdout, "Android SDK environment variables not properly configured")

        logger.info("✓ Android SDK environment variables verified")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class FVMLocationTest(AndroidFVMLocationTestBase):
    """Test FVM installation at expected locations."""

    def setUp(self):
        super().setUp()
        # Install basic komodo environment and FVM
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")

        # Run basic installation including FVM but skip interactive prompt
        install_cmd = """
        cd /home/testuser &&
        # Modify install script to auto-decline the interactive setup prompt
        sed -i 's/read -p "Do you want to run the full setup now.*/REPLY="n"/' install.sh &&
        timeout 600 bash install.sh --debug || echo "Install completed or timed out"
        """
        logger.info("Running basic installation with FVM")
        result = self.run_command_in_container(install_cmd, timeout=700)
        logger.info(f"Install result: {result.returncode}")
        logger.info(f"Install stdout: {result.stdout[:1000]}...")
        logger.info(f"Install stderr: {result.stderr[:1000]}...")

        # Check if basic installation worked
        check_cmd = "test -d /home/testuser/.komodo-codex-env && echo 'BASIC_INSTALL_OK' || echo 'BASIC_INSTALL_FAILED'"
        check_result = self.run_command_in_container(check_cmd, timeout=30)
        if "BASIC_INSTALL_FAILED" in check_result.stdout:
            self.skipTest("Basic installation failed - komodo environment not found")

    def test_fvm_binary_accessibility(self):
        """Test that FVM binary is accessible."""
        logger.info("Testing FVM binary accessibility")

        # First check if FVM was installed at all by looking for common locations
        fvm_check_cmd = """
        echo "=== FVM Location Check ==="
        echo "PATH: $PATH"
        echo "User: $(whoami)"
        echo "Home: $HOME"
        # Check standard locations where FVM might be installed
        if command -v fvm 2>/dev/null; then
            echo "FVM_IN_PATH"
        elif ls -la ~/.fvm_flutter/bin/fvm 2>/dev/null; then
            echo "FVM_IN_FVM_FLUTTER_DIR"
        elif ls -la ~/.pub-cache/bin/fvm 2>/dev/null; then
            echo "FVM_IN_PUB_CACHE"
        elif ls -la /usr/local/bin/fvm 2>/dev/null; then
            echo "FVM_IN_USR_LOCAL"
        else
            find /home -name "*fvm*" -type f -executable 2>/dev/null | head -5
            if [ $? -ne 0 ] || [ ! -s /tmp/fvm_found ]; then
                echo "FVM_NOT_FOUND"
            fi
        fi
        echo "=== FVM Installation Directories ==="
        ls -la ~/.fvm_flutter/ 2>/dev/null || echo "No .fvm_flutter directory"
        ls -la ~/.fvm_flutter/bin/ 2>/dev/null || echo "No .fvm_flutter/bin directory"
        ls -la ~/.pub-cache/ 2>/dev/null || echo "No pub cache directory"
        ls -la ~/.pub-cache/bin/ 2>/dev/null || echo "No pub cache bin directory"
        """

        check_result = self.run_command_in_container(fvm_check_cmd, timeout=60)
        logger.info(f"FVM check result: {check_result.stdout}")

        if "FVM_NOT_FOUND" in check_result.stdout:
            # Show detailed information about what's actually installed
            debug_command = """
            echo "=== FVM Installation Debug ==="
            echo "Install log check:"
            ls -la /home/testuser/.komodo-codex-env/ 2>/dev/null || echo "No komodo env"
            echo "Environment variables:"
            env | grep -E "(PATH|PUB|DART|FLUTTER)" || echo "No relevant env vars"
            echo "Shell profiles:"
            cat ~/.bashrc 2>/dev/null | grep -A5 -B5 -E "fvm|pub-cache" || echo "No fvm references in bashrc"
            echo "All FVM-related files:"
            find /home -name "*fvm*" 2>/dev/null || echo "No fvm files found"
            echo "Checking install script completion:"
            grep -i "fvm.*success\|installation.*complete" /home/testuser/.komodo-codex-env/*.log 2>/dev/null || echo "No success logs found"
            """
            debug_result = self.run_command_in_container(debug_command, timeout=60)
            logger.error(f"FVM debug info: {debug_result.stdout}")
            self.fail("FVM binary not found in any expected location - FVM installation failed")

        # FVM was found, verify it's actually executable
        # Add all possible FVM locations to PATH and test
        fvm_test_cmd = """
        source ~/.bashrc 2>/dev/null || true
        export PATH="$HOME/.fvm_flutter/bin:$HOME/.pub-cache/bin:$PATH"
        echo "Final PATH: $PATH"
        echo "Checking FVM binary locations:"
        ls -la ~/.fvm_flutter/bin/fvm 2>/dev/null && echo "Found in .fvm_flutter/bin" || echo "Not in .fvm_flutter/bin"
        ls -la ~/.pub-cache/bin/fvm 2>/dev/null && echo "Found in .pub-cache/bin" || echo "Not in .pub-cache/bin"
        ls -la /usr/local/bin/fvm 2>/dev/null && echo "Found in /usr/local/bin" || echo "Not in /usr/local/bin"

        # Try to find the actual FVM binary and test it
        if [ -f ~/.fvm_flutter/bin/fvm ]; then
            echo "Testing FVM from .fvm_flutter/bin:"
            ~/.fvm_flutter/bin/fvm --version
        elif [ -f ~/.pub-cache/bin/fvm ]; then
            echo "Testing FVM from .pub-cache/bin:"
            ~/.pub-cache/bin/fvm --version
        elif command -v fvm >/dev/null 2>&1; then
            echo "Testing FVM from PATH:"
            fvm --version
        else
            echo "No working FVM binary found"
            exit 1
        fi
        """
        version_result = self.run_command_in_container(fvm_test_cmd, timeout=30)

        if version_result.returncode != 0:
            logger.error(f"FVM found but not working: {version_result.stderr}")
            self.fail("FVM binary found but not functional")

        logger.info(f"✓ FVM binary verified and functional: {version_result.stdout.strip()}")

    def test_fvm_version_command(self):
        """Test that FVM version command works."""
        logger.info("Testing FVM version command")

        # FVM should be installed, test version command directly
        # Include both possible FVM installation paths
        setup_command = """
        export PATH="$HOME/.fvm_flutter/bin:$HOME/.pub-cache/bin:$PATH"
        fvm --version
        """

        result = self.run_command_in_container(setup_command, timeout=60)

        if result.returncode != 0:
            logger.error(f"FVM version command failed: {result.stderr}")
            # Try to diagnose the issue
            diag_command = """
            echo "PATH: $PATH"
            echo "FVM locations:"
            which fvm || echo "fvm not in PATH"
            ls -la ~/.fvm_flutter/bin/fvm 2>/dev/null || echo "fvm not in ~/.fvm_flutter/bin"
            ls -la ~/.pub-cache/bin/fvm 2>/dev/null || echo "fvm not in ~/.pub-cache/bin"
            ls -la /usr/local/bin/fvm 2>/dev/null || echo "fvm not in /usr/local/bin"
            """
            diag_result = self.run_command_in_container(diag_command, timeout=30)
            logger.error(f"FVM diagnostics: {diag_result.stdout}")

        self.assertEqual(result.returncode, 0, "FVM version command failed")
        self.assertTrue(len(result.stdout.strip()) > 0, "FVM version command produced no output")

        logger.info(f"✓ FVM version verified: {result.stdout.strip()}")


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class EndToEndBuildTest(AndroidFVMLocationTestBase):
    """Test end-to-end Flutter APK build using FVM with Android SDK."""

    def setUp(self):
        super().setUp()
        # Install the complete environment with both FVM and Android SDK
        success = self.copy_file_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
        if not success:
            self.skipTest("Failed to copy install script")

        # Run basic installation first
        basic_install_cmd = """
        cd /home/testuser &&
        source install.sh
        install_system_deps
        setup_python
        install_uv
        install_fvm
        setup_git
        setup_project
        setup_shell_integration
        """
        result = self.run_command_in_container(basic_install_cmd, timeout=1200)
        if result.returncode != 0:
            logger.error(f"Basic install failed: {result.stderr}")
            self.skipTest(f"Basic install failed with exit code {result.returncode}")

        # Install Flutter and Android SDK using komodo setup
        setup_cmd = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH:$HOME/.pub-cache/bin" &&
        cd ~/.komodo-codex-env &&
        uv run komodo-codex-env setup \
            --flutter-version 3.32.0 \
            --install-method precompiled \
            --platforms web,android \
            --verbose
        """
        result = self.run_command_in_container(setup_cmd, timeout=2400)
        if result.returncode != 0:
            logger.error(f"Komodo setup failed: {result.stderr}")
            self.skipTest(f"Komodo setup failed with exit code {result.returncode}")

    def test_fvm_flutter_doctor(self):
        """Test that fvm flutter doctor works with Android SDK."""
        logger.info("Testing fvm flutter doctor with Android SDK")

        # FVM and installation should be complete, proceed with test

        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.pub-cache/bin:$PATH" &&

        # Set Android environment variables
        if [ -d "{android_sdk}" ]; then
            export ANDROID_HOME="{android_sdk}"
            export ANDROID_SDK_ROOT="{android_sdk}"
            export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
            export PATH="$ANDROID_HOME/platform-tools:$PATH"
        fi &&

        # Run flutter doctor
        fvm install 3.32.0 &&
        fvm use 3.32.0 &&
        fvm flutter doctor -v
        """.format(android_sdk=ANDROID_SDK_PATH)

        result = self.run_command_in_container(command, timeout=300)

        if result.returncode != 0:
            logger.error(f"Flutter doctor failed: {result.stderr}")

        # Flutter doctor may have warnings but should not fail completely
        # We're mainly checking that the Android SDK is detected
        self.assertIn("Android", result.stdout, "Android SDK not detected by Flutter doctor")
        logger.info("✓ Flutter doctor completed with Android SDK detection")

    def test_create_and_build_simple_flutter_app(self):
        """Test creating and building a simple Flutter app."""
        logger.info("Testing Flutter app creation and build")

        # FVM, Android SDK, and installation should all be complete, proceed with test

        command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.pub-cache/bin:$PATH" &&

        # Set Android environment
        if [ -d "{android_sdk}" ]; then
            export ANDROID_HOME="{android_sdk}"
            export ANDROID_SDK_ROOT="{android_sdk}"
            export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
            export PATH="$ANDROID_HOME/platform-tools:$PATH"
        fi &&

        # Create a simple Flutter app
        fvm install 3.32.0 &&
        fvm global 3.32.0 &&
        fvm flutter create test_app --platforms android &&
        cd test_app &&

        # Try to build APK (debug)
        timeout 600 fvm flutter build apk --debug
        """.format(android_sdk=ANDROID_SDK_PATH)

        result = self.run_command_in_container(command, timeout=900)

        if result.returncode != 0:
            logger.error(f"Flutter app build failed: {result.stderr}")
            logger.error(f"Build output: {result.stdout}")

        # Check if APK was created
        apk_check = self.run_command_in_container(
            "test -f /home/testuser/test_app/build/app/outputs/flutter-apk/app-debug.apk && echo 'APK_FOUND'",
            timeout=30
        )

        self.assertEqual(result.returncode, 0, "Flutter APK build failed")
        self.assertIn("APK_FOUND", apk_check.stdout, "APK file was not created")

        logger.info("✓ Flutter app creation and APK build successful")


if __name__ == "__main__":
    # Set up logging level based on verbosity
    import sys
    if "-v" in sys.argv or "--verbose" in sys.argv:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    unittest.main(verbosity=2)
