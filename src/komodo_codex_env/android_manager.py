"""Android SDK Manager for building Android APK targets."""

import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import Optional, List, Dict
from rich.console import Console

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager

console = Console()


class AndroidManager:
    """Manages Android SDK installation and configuration for Flutter Android builds."""
    
    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor, dep_manager: DependencyManager):
        self.config = config
        self.executor = executor
        self.dep_manager = dep_manager
        
        # Android SDK paths - default to config value or system path
        self.android_home = config.android_home if config.android_home else Path("/opt/android-sdk")
        self.android_tools_dir = self.android_home / "tools"
        self.android_platform_tools_dir = self.android_home / "platform-tools"
        self.android_cmdline_tools_dir = self.android_home / "cmdline-tools" / "latest"
        
        # Version constants matching the working Dockerfile
        self.cmdline_tools_version = "13114758"  # ANDROID_SDK_TOOLS_VERSION
        self.android_platform_version = "35"    # ANDROID_PLATFORM_VERSION
        self.android_build_tools_version = "35.0.1"  # ANDROID_BUILD_TOOLS_VERSION
        self.android_ndk_version = "28.1.13356709"   # ANDROID_NDK_VERSION
        
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
        """Download and extract Android command line tools."""
        console.print("[blue]Downloading Android SDK command line tools...[/blue]")
        
        # Create Android SDK directory
        self.android_home.mkdir(parents=True, exist_ok=True)
        
        # Download command line tools
        tools_url = self.get_cmdline_tools_url()
        tools_zip_path = self.android_home / "cmdline-tools.zip"
        
        try:
            # Download using curl
            result = self.executor.run_command(
                f"curl -L -o {tools_zip_path} {tools_url}",
                timeout=300  # 5 minutes timeout for download
            )
            
            if result.returncode != 0:
                console.print("[red]✗ Failed to download command line tools[/red]")
                return False
            
            # Extract the zip file
            console.print("[blue]Extracting command line tools...[/blue]")
            with zipfile.ZipFile(tools_zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.android_home)
            
            # Move cmdline-tools to the correct location
            extracted_tools_dir = self.android_home / "cmdline-tools"
            target_tools_dir = self.android_home / "cmdline-tools" / "latest"
            
            # Create the latest directory structure
            target_tools_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Move contents from extracted directory to latest
            if extracted_tools_dir.exists():
                # If extraction created cmdline-tools directory directly
                if (extracted_tools_dir / "bin").exists():
                    shutil.move(str(extracted_tools_dir), str(target_tools_dir))
                else:
                    # Contents are in subdirectory
                    for item in extracted_tools_dir.iterdir():
                        if item.is_dir() and (item / "bin").exists():
                            shutil.move(str(item), str(target_tools_dir))
                            break
            
            # Clean up
            tools_zip_path.unlink(missing_ok=True)
            
            # Verify installation
            sdkmanager_path = target_tools_dir / "bin" / "sdkmanager"
            if sdkmanager_path.exists():
                console.print("[green]✓ Android command line tools extracted[/green]")
                return True
            else:
                console.print("[red]✗ SDK manager not found after extraction[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Failed to download/extract command line tools: {e}[/red]")
            tools_zip_path.unlink(missing_ok=True)
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
        
        # Paths to add
        paths_to_add = [
            str(self.android_cmdline_tools_dir / "bin"),
            str(self.android_platform_tools_dir),
            str(self.android_tools_dir / "bin"),
        ]
        
        try:
            # Add environment variables
            for var_name, var_value in env_vars.items():
                success = self.dep_manager.add_environment_variable(var_name, var_value, profile_path)
                if not success:
                    console.print(f"[yellow]⚠ Failed to set {var_name}[/yellow]")
            
            # Add paths
            for path in paths_to_add:
                success = self.dep_manager.add_to_path(path, profile_path)
                if not success:
                    console.print(f"[yellow]⚠ Failed to add {path} to PATH[/yellow]")
            
            console.print("[green]✓ Android environment variables configured[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Failed to setup environment variables: {e}[/red]")
            return False
    
    def install_sdk_packages(self) -> bool:
        """Install essential Android SDK packages."""
        console.print("[blue]Installing Android SDK packages...[/blue]")
        
        # Set environment variables for this session
        env = os.environ.copy()
        env["ANDROID_HOME"] = str(self.android_home)
        env["ANDROID_SDK_ROOT"] = str(self.android_home)
        
        sdkmanager_path = self.android_cmdline_tools_dir / "bin" / "sdkmanager"
        
        # Essential packages for Flutter Android development (matching Dockerfile)
        packages = [
            "platform-tools",
            f"platforms;android-{self.android_platform_version}",  # Android 15
            "platforms;android-34",  # Previous stable API level (Android 14)
            "platforms;android-33",  # Android 13 for compatibility
            f"build-tools;{self.android_build_tools_version}",    # Latest build tools
            "build-tools;34.0.0",    # Previous build tools for compatibility
            "emulator",
            f"system-images;android-{self.android_platform_version};google_apis;x86_64",  # Latest emulator image
            "cmdline-tools;latest",  # Ensure latest command line tools
            f"ndk;{self.android_ndk_version}",  # NDK for native development
        ]
        
        try:
            # Accept licenses first
            console.print("[blue]Accepting Android SDK licenses...[/blue]")
            self.executor.run_command(
                f"yes | {sdkmanager_path} --licenses",
                check=False,
                timeout=60
            )
            
            # Install packages
            for package in packages:
                console.print(f"[blue]Installing {package}...[/blue]")
                result = self.executor.run_command(
                    f"{sdkmanager_path} '{package}'",
                    check=False,
                    timeout=300
                )
                
                if result.returncode == 0:
                    console.print(f"[green]✓ {package} installed[/green]")
                else:
                    console.print(f"[yellow]⚠ Failed to install {package}[/yellow]")
            
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
            self.android_cmdline_tools_dir / "bin" / "sdkmanager",
            self.android_platform_tools_dir / "adb",
        ]
        
        for tool in essential_tools:
            if not tool.exists():
                console.print(f"[red]✗ Missing tool: {tool}[/red]")
                return False
        
        # Check if platforms directory exists
        platforms_dir = self.android_home / "platforms"
        if not platforms_dir.exists() or not any(platforms_dir.iterdir()):
            console.print("[red]✗ No Android platforms installed[/red]")
            return False
        
        # Check if build-tools directory exists
        build_tools_dir = self.android_home / "build-tools"
        if not build_tools_dir.exists() or not any(build_tools_dir.iterdir()):
            console.print("[red]✗ No Android build tools installed[/red]")
            return False
        
        console.print("[green]✓ Android SDK installation verified[/green]")
        return True
    
    def install_android_sdk(self) -> bool:
        """Complete Android SDK installation process."""
        console.print("[bold blue]Installing Android SDK...[/bold blue]")
        
        # Check if already installed
        if self.is_android_sdk_installed():
            console.print("[green]✓ Android SDK already installed[/green]")
            return self.verify_installation()
        
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
            return False
        
        # Install SDK packages
        if not self.install_sdk_packages():
            return False
        
        # Verify installation
        return self.verify_installation()
    
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
            # Create the directory structure
            self.android_home.mkdir(parents=True, exist_ok=True)
            
            # Set ownership to current user (similar to Dockerfile approach)
            import getpass
            current_user = getpass.getuser()
            
            # Change ownership to current user (may require sudo)
            result = self.executor.run_command(
                f"sudo chown -R {current_user}:{current_user} {self.android_home}",
                check=False
            )
            
            if result.returncode != 0:
                console.print("[yellow]⚠ Could not change directory ownership, trying without sudo...[/yellow]")
                # Try to create in user directory instead
                fallback_home = Path.home() / "Android" / "Sdk" 
                fallback_home.mkdir(parents=True, exist_ok=True)
                # Update paths to use fallback
                self.android_home = fallback_home
                self.android_tools_dir = self.android_home / "tools"
                self.android_platform_tools_dir = self.android_home / "platform-tools"
                self.android_cmdline_tools_dir = self.android_home / "cmdline-tools" / "latest"
                console.print(f"[blue]Using fallback directory: {self.android_home}[/blue]")
            
            console.print(f"[green]✓ Android SDK directory ready: {self.android_home}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Failed to setup Android directories: {e}[/red]")
            return False