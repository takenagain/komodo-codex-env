#!/usr/bin/env python3
"""
Standalone Android SDK Installation Script for Flutter Development
This script can be run independently to install Android SDK for APK building.
"""

import os
import sys
import platform
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict

def print_status(message: str, status: str = "info"):
    """Print colored status messages."""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "reset": "\033[0m"       # Reset
    }
    
    color = colors.get(status, colors["info"])
    reset = colors["reset"]
    print(f"{color}{message}{reset}")

def run_command(command: str, cwd: Optional[Path] = None, timeout: int = 300) -> bool:
    """Run a shell command and return success status."""
    print_status(f"Executing: {command}", "info")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                print(result.stdout.strip())
            return True
        else:
            print_status(f"Command failed with exit code {result.returncode}", "error")
            if result.stderr:
                print_status(f"Error: {result.stderr.strip()}", "error")
            return False
            
    except subprocess.TimeoutExpired:
        print_status(f"Command timed out after {timeout} seconds", "error")
        return False
    except Exception as e:
        print_status(f"Command execution failed: {e}", "error")
        return False

def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system."""
    try:
        result = subprocess.run(
            f"command -v {command}",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def get_java_version() -> Optional[str]:
    """Get installed Java version."""
    if not check_command_exists("java") or not check_command_exists("javac"):
        return None
    
    try:
        result = subprocess.run(
            "java -version",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version_output = result.stderr or result.stdout
            lines = version_output.split('\n')
            for line in lines:
                if 'version' in line.lower():
                    import re
                    match = re.search(r'version "([^"]+)"', line)
                    if match:
                        return match.group(1)
            return version_output.strip()
    except Exception:
        pass
    return None

def install_java() -> bool:
    """Install Java Development Kit."""
    print_status("Installing Java Development Kit...", "info")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Try to detect package manager
        if check_command_exists("apt"):
            return run_command("sudo apt update && sudo apt install -y openjdk-17-jdk")
        elif check_command_exists("yum"):
            return run_command("sudo yum install -y java-17-openjdk-devel")
        elif check_command_exists("pacman"):
            return run_command("sudo pacman -S --noconfirm jdk17-openjdk")
        else:
            print_status("No supported package manager found", "error")
            return False
    elif system == "darwin":  # macOS
        if check_command_exists("brew"):
            success = run_command("brew install openjdk@17")
            if success:
                # Create symlink for system java
                run_command(
                    "sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk"
                )
            return success
        else:
            print_status("Homebrew not found. Please install Java manually from https://adoptium.net/temurin/releases/", "warning")
            return False
    else:
        print_status(f"Unsupported OS for automatic Java installation: {system}", "error")
        return False

def get_cmdline_tools_url() -> str:
    """Get the download URL for Android command line tools."""
    system = platform.system().lower()
    version = "11076708"  # Latest stable version
    
    base_url = "https://dl.google.com/android/repository"
    
    if system == "linux":
        return f"{base_url}/commandlinetools-linux-{version}_latest.zip"
    elif system == "darwin":  # macOS
        return f"{base_url}/commandlinetools-mac-{version}_latest.zip"
    elif system == "windows":
        return f"{base_url}/commandlinetools-win-{version}_latest.zip"
    else:
        return f"{base_url}/commandlinetools-linux-{version}_latest.zip"

def download_and_extract_cmdline_tools(android_home: Path) -> bool:
    """Download and extract Android command line tools."""
    print_status("Downloading Android SDK command line tools...", "info")
    
    # Create Android SDK directory
    android_home.mkdir(parents=True, exist_ok=True)
    
    # Download command line tools
    tools_url = get_cmdline_tools_url()
    tools_zip_path = android_home / "cmdline-tools.zip"
    
    try:
        # Download using curl
        if not run_command(f"curl -L -o {tools_zip_path} {tools_url}", timeout=300):
            print_status("Failed to download command line tools", "error")
            return False
        
        # Extract the zip file
        print_status("Extracting command line tools...", "info")
        with zipfile.ZipFile(tools_zip_path, 'r') as zip_ref:
            zip_ref.extractall(android_home)
        
        # Move cmdline-tools to the correct location
        extracted_tools_dir = android_home / "cmdline-tools"
        target_tools_dir = android_home / "cmdline-tools" / "latest"
        
        # Create the latest directory structure
        target_tools_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Move contents from extracted directory to latest
        if extracted_tools_dir.exists():
            if (extracted_tools_dir / "bin").exists():
                shutil.move(str(extracted_tools_dir), str(target_tools_dir))
            else:
                for item in extracted_tools_dir.iterdir():
                    if item.is_dir() and (item / "bin").exists():
                        shutil.move(str(item), str(target_tools_dir))
                        break
        
        # Clean up
        tools_zip_path.unlink(missing_ok=True)
        
        # Verify installation
        sdkmanager_path = target_tools_dir / "bin" / "sdkmanager"
        if sdkmanager_path.exists():
            print_status("Android command line tools extracted successfully", "success")
            return True
        else:
            print_status("SDK manager not found after extraction", "error")
            return False
            
    except Exception as e:
        print_status(f"Failed to download/extract command line tools: {e}", "error")
        tools_zip_path.unlink(missing_ok=True)
        return False

def setup_environment_variables(android_home: Path) -> bool:
    """Set up Android SDK environment variables."""
    print_status("Setting up Android environment variables...", "info")
    
    # Determine shell profile
    shell = os.getenv("SHELL", "")
    home = Path.home()
    
    if "zsh" in shell:
        profile_path = home / ".zshrc"
    elif "bash" in shell:
        profile_path = home / ".bashrc"
    else:
        profile_path = home / ".profile"
    
    try:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing content
        existing_content = ""
        if profile_path.exists():
            existing_content = profile_path.read_text()
        
        # Check if already configured
        if str(android_home) in existing_content:
            print_status("Android environment variables already configured", "warning")
            return True
        
        # Add environment variables
        env_lines = [
            "\n# Android SDK Environment Variables - Added by Android SDK Installer",
            f'export ANDROID_HOME="{android_home}"',
            f'export ANDROID_SDK_ROOT="{android_home}"',
            f'export PATH="$PATH:{android_home}/cmdline-tools/latest/bin"',
            f'export PATH="$PATH:{android_home}/platform-tools"',
            f'export PATH="$PATH:{android_home}/tools/bin"',
        ]
        
        with profile_path.open("a") as f:
            f.write("\n".join(env_lines) + "\n")
        
        print_status(f"Environment variables added to {profile_path}", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to setup environment variables: {e}", "error")
        return False

def install_sdk_packages(android_home: Path) -> bool:
    """Install essential Android SDK packages."""
    print_status("Installing Android SDK packages...", "info")
    
    # Set environment variables for this session
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(android_home)
    env["ANDROID_SDK_ROOT"] = str(android_home)
    
    sdkmanager_path = android_home / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    
    # Essential packages for Flutter Android development
    packages = [
        "platform-tools",
        "platforms;android-34",
        "platforms;android-33",
        "build-tools;34.0.0",
        "build-tools;33.0.1",
        "emulator",
        "system-images;android-34;google_apis;x86_64",
    ]
    
    try:
        # Accept licenses first
        print_status("Accepting Android SDK licenses...", "info")
        subprocess.run(
            f"yes | {sdkmanager_path} --licenses",
            shell=True,
            env=env,
            timeout=60,
            capture_output=True
        )
        
        # Install packages
        for package in packages:
            print_status(f"Installing {package}...", "info")
            result = subprocess.run(
                f"{sdkmanager_path} '{package}'",
                shell=True,
                env=env,
                timeout=300,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print_status(f"✓ {package} installed", "success")
            else:
                print_status(f"⚠ Failed to install {package}", "warning")
        
        print_status("Android SDK packages installation completed", "success")
        return True
        
    except Exception as e:
        print_status(f"Failed to install SDK packages: {e}", "error")
        return False

def verify_installation(android_home: Path) -> bool:
    """Verify Android SDK installation."""
    print_status("Verifying Android SDK installation...", "info")
    
    # Check if essential tools exist
    essential_tools = [
        android_home / "cmdline-tools" / "latest" / "bin" / "sdkmanager",
        android_home / "platform-tools" / "adb",
    ]
    
    for tool in essential_tools:
        if not tool.exists():
            print_status(f"✗ Missing tool: {tool}", "error")
            return False
    
    # Check if platforms directory exists
    platforms_dir = android_home / "platforms"
    if not platforms_dir.exists() or not any(platforms_dir.iterdir()):
        print_status("✗ No Android platforms installed", "error")
        return False
    
    # Check if build-tools directory exists
    build_tools_dir = android_home / "build-tools"
    if not build_tools_dir.exists() or not any(build_tools_dir.iterdir()):
        print_status("✗ No Android build tools installed", "error")
        return False
    
    print_status("✓ Android SDK installation verified", "success")
    return True

def main():
    """Main installation process."""
    print_status("=== Android SDK Installation for Flutter Development ===", "info")
    
    # Setup paths
    home = Path.home()
    android_home = home / "Android" / "Sdk"
    
    print_status(f"Installing Android SDK to: {android_home}", "info")
    
    # Check if already installed
    if (android_home.exists() and 
        (android_home / "cmdline-tools" / "latest" / "bin" / "sdkmanager").exists()):
        print_status("Android SDK already installed", "warning")
        if verify_installation(android_home):
            print_status("Android SDK installation is valid", "success")
            return True
    
    # Check Java installation
    java_version = get_java_version()
    if java_version:
        print_status(f"✓ Java already installed: {java_version}", "success")
    else:
        print_status("Java not found, installing...", "info")
        if not install_java():
            print_status("Java installation failed", "error")
            return False
        
        # Verify Java installation
        java_version = get_java_version()
        if java_version:
            print_status(f"✓ Java installed: {java_version}", "success")
        else:
            print_status("Java installation verification failed", "error")
            return False
    
    # Download and extract command line tools
    if not download_and_extract_cmdline_tools(android_home):
        print_status("Failed to download/extract Android SDK tools", "error")
        return False
    
    # Setup environment variables
    if not setup_environment_variables(android_home):
        print_status("Failed to setup environment variables", "error")
        return False
    
    # Install SDK packages
    if not install_sdk_packages(android_home):
        print_status("Failed to install SDK packages", "error")
        return False
    
    # Verify installation
    if not verify_installation(android_home):
        print_status("Installation verification failed", "error")
        return False
    
    print_status("=== Android SDK Installation Complete ===", "success")
    print_status("", "info")
    print_status("Next steps:", "info")
    print_status("1. Restart your terminal or run: source ~/.zshrc (or ~/.bashrc)", "info")
    print_status("2. Verify with: flutter doctor", "info")
    print_status("3. Accept licenses with: flutter doctor --android-licenses", "info")
    print_status("4. List devices with: flutter devices", "info")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_status("\nInstallation cancelled by user", "warning")
        sys.exit(1)
    except Exception as e:
        print_status(f"Installation failed with error: {e}", "error")
        sys.exit(1)