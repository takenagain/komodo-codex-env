"""Android SDK Manager for building Android APK targets."""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Dict

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager

try:
    from rich.console import Console
    console = Console()
except ImportError:
    # Fallback console for environments without rich
    class SimpleConsole:
        def print(self, message: str, **kwargs):
            print(message)
    console = SimpleConsole()


class AndroidManager:
    """Manages Android SDK installation and configuration for Flutter Android builds."""

    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor, dep_manager: DependencyManager):
        self.config = config
        self.executor = executor
        self.dep_manager = dep_manager

        # Android SDK paths - use user directory to avoid sudo requirements
        if config.android_home:
            self.android_home = Path(config.android_home)
        else:
            # Use user directory by default (no sudo required)
            self.android_home = Path.home() / ".android-sdk"
        
        self.android_tools_dir = self.android_home / "tools"
        self.android_platform_tools_dir = self.android_home / "platform-tools"
        self.android_cmdline_tools_dir = self.android_home / "cmdline-tools" / "latest"

        # Version constants matching the working Dockerfile and config
        self.cmdline_tools_version = config.android_sdk_tools_version  # Use config value
        self.android_platform_version = config.android_api_level    # Use config value
        self.android_build_tools_version = config.android_build_tools_version  # Use config value
        self.android_ndk_version = config.android_ndk_version   # Use config value

    def _get_android_env(self) -> Dict[str, str]:
        """Get Android environment variables."""
        return {
            "ANDROID_HOME": str(self.android_home),
            "ANDROID_SDK_ROOT": str(self.android_home),
            "PATH": f"{self.android_cmdline_tools_dir / 'bin'}:{self.android_platform_tools_dir}:{os.environ.get('PATH', '')}"
        }

    def is_android_sdk_installed(self) -> bool:
        """Check if Android SDK is already installed."""
        return (
            self.android_home.exists() and
            self.android_cmdline_tools_dir.exists() and
            (self.android_cmdline_tools_dir / "bin" / "sdkmanager").exists()
        )

    def is_java_installed(self) -> bool:
        """Check if Java/JDK is installed."""
        return self.executor.check_command_exists("java") and self.executor.check_command_exists("javac")

    def get_java_version(self) -> Optional[str]:
        """Get installed Java version."""
        if not self.is_java_installed():
            return None

        try:
            result = self.executor.run_command("java -version", check=False, capture_output=True)
            if result.returncode == 0:
                # Java version is typically in stderr
                version_output = result.stderr or result.stdout
                # Extract version number (e.g., "17.0.1" from version string)
                lines = version_output.split('\n')
                for line in lines:
                    if 'version' in line.lower():
                        # Look for version pattern like "17.0.1" or "1.8.0_xxx"
                        import re
                        match = re.search(r'version "([^"]+)"', line)
                        if match:
                            return match.group(1)
                return version_output.strip()
        except Exception:
            pass
        return None

    def install_java(self) -> bool:
        """Install Java Development Kit (JDK)."""
        console.print("[blue]Installing Java Development Kit...[/blue]")

        system_info = self.dep_manager.get_system_info()
        os_name = system_info.get("os", "").lower()

        java_packages = []

        if os_name == "linux":
            # Use OpenJDK 21 (matching the working Dockerfile)
            java_packages = ["openjdk-21-jdk"]
        elif os_name == "darwin":  # macOS
            # Check if Homebrew is available
            if self.executor.check_command_exists("brew"):
                try:
                    result = self.executor.run_command("brew install openjdk@21", check=False)
                    if result.returncode == 0:
                        # Create symlink for system java
                        self.executor.run_command(
                            "sudo ln -sfn /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-21.jdk",
                            check=False
                        )
                        console.print("[green]✓ Java installed via Homebrew[/green]")
                        return True
                except Exception:
                    pass

            console.print("[yellow]Please install Java manually on macOS[/yellow]")
            console.print("[blue]Visit: https://adoptium.net/temurin/releases/[/blue]")
            return False
        else:
            console.print(f"[yellow]Unsupported OS for automatic Java installation: {os_name}[/yellow]")
            return False

        # Install Java packages on Linux
        if java_packages:
            success = self.dep_manager.install_dependencies(java_packages)
            if success:
                console.print("[green]✓ Java Development Kit installed[/green]")
            else:
                console.print("[red]✗ Failed to install Java Development Kit[/red]")
            return success

        return False

    def get_cmdline_tools_url(self) -> str:
        """Get the download URL for Android command line tools."""
        system_info = self.dep_manager.get_system_info()
        os_name = system_info.get("os", "").lower()

        base_url = "https://dl.google.com/android/repository"

        if os_name == "linux":
            return f"{base_url}/commandlinetools-linux-{self.cmdline_tools_version}_latest.zip"
        elif os_name == "darwin":  # macOS
            return f"{base_url}/commandlinetools-mac-{self.cmdline_tools_version}_latest.zip"
        elif os_name == "windows":
            return f"{base_url}/commandlinetools-win-{self.cmdline_tools_version}_latest.zip"
        else:
            # Default to Linux
            return f"{base_url}/commandlinetools-linux-{self.cmdline_tools_version}_latest.zip"

    def download_and_extract_cmdline_tools(self) -> bool:
        """Download and extract Android command line tools (following dockerfile approach)."""
        console.print("[blue]Downloading Android SDK command line tools...[/blue]")

        # Create Android SDK directory in user space (no sudo required)
        self.android_home.mkdir(parents=True, exist_ok=True)
        console.print(f"[blue]Using Android SDK directory: {self.android_home}[/blue]")

        # Clean up any existing cmdline-tools directory to avoid conflicts
        cmdline_tools_base = self.android_home / "cmdline-tools"
        if cmdline_tools_base.exists():
            console.print("[blue]Removing existing cmdline-tools directory...[/blue]")
            shutil.rmtree(cmdline_tools_base)

        # Download command line tools
        tools_url = self.get_cmdline_tools_url()
        tools_zip_path = self.android_home / "cmdline-tools.zip"

        try:
            # Clean up any existing zip file
            tools_zip_path.unlink(missing_ok=True)

            # Download using curl (following dockerfile approach)
            console.print(f"[blue]Downloading from: {tools_url}[/blue]")
            result = self.executor.run_command(
                f"curl -L -o {tools_zip_path} {tools_url}",
                timeout=300  # 5 minutes timeout for download
            )

            if result.returncode != 0:
                console.print("[red]✗ Failed to download command line tools[/red]")
                console.print(f"[red]Error: {result.stderr if result.stderr else 'Unknown error'}[/red]")
                return False

            console.print("[green]✓ Command line tools downloaded successfully[/green]")

            # Extract the zip file - following dockerfile approach exactly
            console.print("[blue]Extracting command line tools...[/blue]")

            # Create clean cmdline-tools directory
            cmdline_tools_base.mkdir(parents=True, exist_ok=True)

            # Extract zip directly to cmdline-tools directory
            with zipfile.ZipFile(tools_zip_path, 'r') as zip_ref:
                zip_ref.extractall(cmdline_tools_base)

            # Following dockerfile: mv cmdline-tools/cmdline-tools cmdline-tools/latest
            extracted_cmdline_dir = cmdline_tools_base / "cmdline-tools"
            target_latest_dir = cmdline_tools_base / "latest"

            if extracted_cmdline_dir.exists():
                # Move cmdline-tools to latest (target should not exist at this point)
                shutil.move(str(extracted_cmdline_dir), str(target_latest_dir))
                console.print("[blue]✓ Moved cmdline-tools to latest directory[/blue]")
            else:
                console.print("[red]✗ Expected cmdline-tools directory not found after extraction[/red]")
                # Show what was actually extracted for debugging
                extracted_contents = list(cmdline_tools_base.iterdir())
                console.print(f"[red]Found in extraction: {[p.name for p in extracted_contents]}[/red]")
                return False

            # Clean up
            tools_zip_path.unlink(missing_ok=True)

            # Verify installation
            sdkmanager_path = target_latest_dir / "bin" / "sdkmanager"
            if sdkmanager_path.exists():
                # Make sdkmanager executable
                import stat
                sdkmanager_path.chmod(sdkmanager_path.stat().st_mode | stat.S_IEXEC)
                console.print("[green]✓ Android command line tools extracted successfully[/green]")
                return True
            else:
                console.print("[red]✗ SDK manager not found after extraction[/red]")
                console.print(f"[red]Expected at: {sdkmanager_path}[/red]")
                # Debug: show what's in the latest directory
                if target_latest_dir.exists():
                    latest_contents = list(target_latest_dir.iterdir())
                    console.print(f"[red]Contents of latest dir: {[p.name for p in latest_contents]}[/red]")
                return False

        except Exception as e:
            console.print(f"[red]✗ Failed to download/extract command line tools: {e}[/red]")
            tools_zip_path.unlink(missing_ok=True)
            # Clean up cmdline-tools directory on error
            if cmdline_tools_base.exists():
                shutil.rmtree(cmdline_tools_base)
            return False

    def setup_environment_variables(self) -> bool:
        """Set up Android SDK environment variables."""
        console.print("[blue]Setting up Android environment variables...[/blue]")

        profile_path = self.config.get_shell_profile()

        # Environment variables to add
        env_vars = {
            "ANDROID_HOME": str(self.android_home),
            "ANDROID_SDK_ROOT": str(self.android_home),
        }
        
        console.print(f"[blue]Setting ANDROID_HOME to: {self.android_home}[/blue]")

        # Paths to add (only existing directories)
        paths_to_add = []
        potential_paths = [
            str(self.android_cmdline_tools_dir / "bin"),
            str(self.android_platform_tools_dir),
            str(self.android_tools_dir / "bin"),
        ]

        for path in potential_paths:
            if Path(path).exists():
                paths_to_add.append(path)

        try:
            # Set environment variables immediately for current process
            for var_name, var_value in env_vars.items():
                os.environ[var_name] = var_value
                console.print(f"[green]✓ Set {var_name}={var_value}[/green]")

            # Add environment variables to profile
            for var_name, var_value in env_vars.items():
                success = self.dep_manager.add_environment_variable(var_name, var_value, profile_path)
                if not success:
                    console.print(f"[yellow]⚠ Failed to persist {var_name} to profile[/yellow]")

            # Add paths to current PATH
            current_path = os.environ.get("PATH", "")
            for path in paths_to_add:
                if path not in current_path:
                    os.environ["PATH"] = f"{path}:{current_path}"
                    console.print(f"[green]✓ Added {path} to current PATH[/green]")

            # Add paths to profile for persistence
            for path in paths_to_add:
                success = self.dep_manager.add_to_path(path, profile_path)
                if not success:
                    console.print(f"[yellow]⚠ Failed to persist {path} to profile[/yellow]")

            console.print("[green]✓ Android environment variables configured[/green]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to setup environment variables: {e}[/red]")
            return False

    def install_sdk_packages(self) -> bool:
        """Install essential Android SDK packages."""
        console.print("[blue]Installing Android SDK packages...[/blue]")

        sdkmanager_path = self.android_cmdline_tools_dir / "bin" / "sdkmanager"

        # Verify sdkmanager exists
        if not sdkmanager_path.exists():
            console.print(f"[red]✗ SDK manager not found at {sdkmanager_path}[/red]")
            return False

        # Essential packages for Flutter Android development (matching Dockerfile)
        packages = [
            "platform-tools",
            f"platforms;android-{self.android_platform_version}",  # Latest platform
            "platforms;android-34",  # Previous stable API level (Android 14)
            f"build-tools;{self.android_build_tools_version}",    # Latest build tools
            "build-tools;34.0.0",    # Previous build tools for compatibility
        ]

        # Optional packages (install if possible but don't fail if they don't work)
        optional_packages = [
            "emulator",
            f"system-images;android-{self.android_platform_version};google_apis;x86_64",
            "cmdline-tools;latest",
            f"ndk;{self.android_ndk_version}",
        ]

        try:
            # Accept licenses first (following dockerfile approach)
            console.print("[blue]Accepting Android SDK licenses...[/blue]")
            result = self.executor.run_command(
                f"yes | {sdkmanager_path} --licenses",
                check=False,
                timeout=60
            )

            if result.returncode != 0:
                console.print("[yellow]⚠ License acceptance may have had issues, continuing...[/yellow]")

            # Install essential packages
            console.print("[blue]Installing essential SDK packages...[/blue]")
            for package in packages:
                console.print(f"[blue]Installing {package}...[/blue]")
                result = self.executor.run_command(
                    f'"{sdkmanager_path}" "{package}"',
                    check=False,
                    timeout=300
                )

                if result.returncode == 0:
                    console.print(f"[green]✓ {package} installed[/green]")
                else:
                    console.print(f"[red]✗ Failed to install {package}[/red]")
                    console.print(f"[red]Error: {result.stderr if result.stderr else 'Unknown error'}[/red]")
                    # Don't fail completely, continue with other packages
                    console.print("[yellow]⚠ Continuing with remaining packages...[/yellow]")

            # Install optional packages (best effort)
            console.print("[blue]Installing optional SDK packages...[/blue]")
            for package in optional_packages:
                console.print(f"[blue]Installing {package}...[/blue]")
                result = self.executor.run_command(
                    f'"{sdkmanager_path}" "{package}"',
                    check=False,
                    timeout=300
                )

                if result.returncode == 0:
                    console.print(f"[green]✓ {package} installed[/green]")
                else:
                    console.print(f"[yellow]⚠ Failed to install optional package {package}[/yellow]")

            console.print("[green]✓ Android SDK packages installation completed[/green]")
            return True

        except Exception as e:
            console.print(f"[red]✗ Failed to install SDK packages: {e}[/red]")
            return False

    def install_system_dependencies(self) -> bool:
        """Install system dependencies required for Android development (matching Dockerfile)."""
        console.print("[blue]Installing system dependencies for Android development...[/blue]")

        system_info = self.dep_manager.get_system_info()
        os_name = system_info.get("os", "").lower()

        if os_name == "linux":
            # System packages from the working Dockerfile
            system_packages = [
                "jq", "nodejs", "npm", "wget", "zip", "unzip", "git",
                "openssh-client", "curl", "bc", "software-properties-common",
                "build-essential", "ruby-full", "ruby-bundler", "libstdc++6",
                "libpulse0", "libglu1-mesa", "locales", "lcov", "libsqlite3-dev",
                # For x86 emulators
                "libxtst6", "libnss3-dev", "libnspr4", "libxss1",
                "libatk-bridge2.0-0", "libgtk-3-0", "libgdk-pixbuf2.0-0",
                # For Linux builds (Flutter desktop)
                "xz-utils", "clang", "cmake", "ninja-build", "pkg-config",
                "libgtk-3-dev", "liblzma-dev", "libstdc++-12-dev"
            ]

            success = self.dep_manager.install_dependencies(system_packages)
            if success:
                console.print("[green]✓ System dependencies installed[/green]")
            else:
                console.print("[yellow]⚠ Some system dependencies may have failed to install[/yellow]")
            return success
        else:
            console.print(f"[yellow]System dependency installation not implemented for {os_name}[/yellow]")
            return True  # Don't fail on non-Linux systems

    def verify_installation(self) -> bool:
        """Verify Android SDK installation."""
        console.print("[blue]Verifying Android SDK installation...[/blue]")

        # Check if essential tools exist
        essential_tools = [
            (self.android_cmdline_tools_dir / "bin" / "sdkmanager", "SDK Manager"),
            (self.android_platform_tools_dir / "adb", "ADB"),
            (self.android_platform_tools_dir / "fastboot", "Fastboot"),
        ]

        all_good = True

        for tool_path, tool_name in essential_tools:
            if tool_path.exists():
                console.print(f"[green]✓ {tool_name} found at {tool_path}[/green]")
            else:
                console.print(f"[red]✗ {tool_name} not found at {tool_path}[/red]")
                all_good = False

        # Check if platforms are installed
        platforms_dir = self.android_home / "platforms"
        if platforms_dir.exists():
            platforms = list(platforms_dir.glob("android-*"))
            if platforms:
                console.print(f"[green]✓ Found {len(platforms)} platform(s): {', '.join(p.name for p in platforms)}[/green]")
            else:
                console.print("[yellow]⚠ No platforms installed[/yellow]")
                all_good = False
        else:
            console.print("[red]✗ Platforms directory not found[/red]")
            all_good = False

        # Check if build-tools are installed
        build_tools_dir = self.android_home / "build-tools"
        if build_tools_dir.exists():
            build_tools = list(build_tools_dir.glob("*"))
            if build_tools:
                console.print(f"[green]✓ Found {len(build_tools)} build-tools version(s): {', '.join(bt.name for bt in build_tools)}[/green]")
            else:
                console.print("[yellow]⚠ No build-tools installed[/yellow]")
                all_good = False
        else:
            console.print("[red]✗ Build-tools directory not found[/red]")
            all_good = False

        # Test sdkmanager command
        sdkmanager_path = self.android_cmdline_tools_dir / "bin" / "sdkmanager"
        if sdkmanager_path.exists():
            try:
                result = self.executor.run_command(
                    f'"{sdkmanager_path}" --list',
                    check=False,
                    timeout=30
                )
                if result.returncode == 0:
                    console.print("[green]✓ SDK Manager command working[/green]")
                else:
                    console.print("[yellow]⚠ SDK Manager command failed[/yellow]")
                    all_good = False
            except Exception as e:
                console.print(f"[yellow]⚠ Could not test SDK Manager: {e}[/yellow]")
                all_good = False

        if all_good:
            console.print("[green]✓ Android SDK installation verified successfully[/green]")
        else:
            console.print("[yellow]⚠ Android SDK verification completed with warnings[/yellow]")

        return all_good

    def install_android_sdk(self) -> bool:
        """Complete Android SDK installation process."""
        console.print("[bold blue]Installing Android SDK...[/bold blue]")
        console.print(f"[blue]Target installation directory: {self.android_home}[/blue]")
        console.print(f"[blue]Command line tools will be at: {self.android_cmdline_tools_dir}[/blue]")

        # Check if already installed
        if self.is_android_sdk_installed():
            console.print("[green]✓ Android SDK already installed[/green]")
            return self.verify_installation()

        # Setup Android directories first (in user space)
        if not self.setup_android_directories():
            console.print("[red]✗ Failed to setup Android directories[/red]")
            return False

        # Install system dependencies first
        if not self.install_system_dependencies():
            console.print("[yellow]⚠ System dependencies installation had issues, continuing...[/yellow]")

        # Install Java if not present
        if not self.is_java_installed():
            if not self.install_java():
                console.print("[red]✗ Java installation failed[/red]")
                return False
        else:
            java_version = self.get_java_version()
            console.print(f"[green]✓ Java already installed: {java_version}[/green]")

        # Download and extract command line tools
        if not self.download_and_extract_cmdline_tools():
            return False

        # Setup environment variables
        if not self.setup_environment_variables():
            console.print("[red]✗ Failed to setup environment variables[/red]")
            return False

        # Install SDK packages
        if not self.install_sdk_packages():
            console.print("[yellow]⚠ SDK packages installation had issues, but continuing...[/yellow]")

        # Verify installation
        result = self.verify_installation()
        
        if result:
            console.print("[green]✓ Android SDK installation completed successfully![/green]")
            console.print(f"[blue]Android SDK location: {self.android_home}[/blue]")
            console.print(f"[blue]To use with Flutter, set: export ANDROID_HOME={self.android_home}[/blue]")
        
        return result

    def get_android_info(self) -> Dict[str, str]:
        """Get Android SDK information."""
        info = {}

        if self.is_android_sdk_installed():
            info["status"] = "installed"
            info["android_home"] = str(self.android_home)

            # Get SDK version if possible
            try:
                sdkmanager_path = self.android_cmdline_tools_dir / "bin" / "sdkmanager"
                result = self.executor.run_command(
                    f"{sdkmanager_path} --version",
                    check=False,
                    capture_output=True
                )
                if result.returncode == 0:
                    info["sdk_version"] = result.stdout.strip()
            except Exception:
                pass
        else:
            info["status"] = "not_installed"

        # Java information
        if self.is_java_installed():
            info["java_status"] = "installed"
            java_version = self.get_java_version()
            if java_version:
                info["java_version"] = java_version
        else:
            info["java_status"] = "not_installed"

        return info

    def setup_android_directories(self) -> bool:
        """Setup Android SDK directories with proper permissions."""
        console.print("[blue]Setting up Android SDK directories...[/blue]")

        try:
            # Check if /opt/android-sdk is writable (should be set up by install.sh)
            if str(self.android_home).startswith('/opt/') and not os.access(str(self.android_home.parent), os.W_OK):
                console.print(f"[red]✗ {self.android_home.parent} is not writable[/red]")
                console.print("[red]Please ensure install.sh was run to set up /opt directory permissions[/red]")
                return False

            # Create the directory structure
            self.android_home.mkdir(parents=True, exist_ok=True)
            
            # Verify we can write to the directory
            if not os.access(str(self.android_home), os.W_OK):
                console.print(f"[red]✗ Cannot write to {self.android_home}[/red]")
                return False
            
            # Create additional required directories
            (self.android_home / "platforms").mkdir(exist_ok=True)
            (self.android_home / "build-tools").mkdir(exist_ok=True)
            (self.android_home / "platform-tools").mkdir(exist_ok=True)
            
            console.print(f"[green]✓ Android SDK directory ready: {self.android_home}[/green]")
            console.print("[blue]SDK will be accessible without sudo requirements[/blue]")
            return True

        except PermissionError as e:
            console.print(f"[red]✗ Permission denied creating Android directories: {e}[/red]")
            console.print("[red]Please ensure install.sh was run to set up /opt directory permissions[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Failed to setup Android directories: {e}[/red]")
            return False
