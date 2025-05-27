#!/usr/bin/env python3
"""
Enhanced Android SDK and FVM Location Tests with Space Optimization

This test runner includes:
- Pre-test space optimization
- Enhanced error handling
- Better container resource management
- Comprehensive verification
"""

import subprocess
import time
import unittest
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import rich
    from rich.console import Console
    from rich.logging import RichHandler
    console = Console()
except ImportError:
    rich = None
    console = None

# Test configuration
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"
VERIFICATION_SCRIPT = PROJECT_ROOT / "scripts" / "verify_installation.py"
OPTIMIZATION_SCRIPT = PROJECT_ROOT / "scripts" / "optimize_docker_space.sh"

# Container settings optimized for space
CONTAINER_CONFIG = {
    "tmpfs_size": "2g",
}

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


class OptimizedAndroidFVMTest:
    """Optimized test runner for Android SDK and FVM location tests."""
    
    def __init__(self):
        self.container_id = None
        self.container_name = None
        self.image_name = "komodo-android-fvm-optimized"
        
    def log_step(self, message: str):
        """Log a test step."""
        if console:
            console.print(f"\n[bold blue]🔧 {message}[/bold blue]")
        else:
            logger.info(f"🔧 {message}")
    
    def log_success(self, message: str):
        """Log success."""
        if console:
            console.print(f"[bold green]✅ {message}[/bold green]")
        else:
            logger.info(f"✅ {message}")
    
    def log_error(self, message: str):
        """Log error."""
        if console:
            console.print(f"[bold red]❌ {message}[/bold red]")
        else:
            logger.error(f"❌ {message}")
    
    def check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                check=True, 
                capture_output=True
            )
            self.log_success("Docker is available")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_error("Docker is not available")
            return False
    
    def build_optimized_image(self) -> bool:
        """Build optimized Docker image for testing."""
        self.log_step("Building optimized Docker image...")
        
        try:
            result = subprocess.run(
                [
                    "docker", "build", 
                    "-t", self.image_name, 
                    "-f", str(DOCKERFILE), 
                    str(PROJECT_ROOT)
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode != 0:
                self.log_error(f"Failed to build Docker image: {result.stderr}")
                return False
                
            self.log_success("Docker image built successfully")
            return True
            
        except subprocess.TimeoutExpired:
            self.log_error("Docker build timed out")
            return False
        except Exception as e:
            self.log_error(f"Docker build failed: {e}")
            return False
    
    def start_optimized_container(self) -> bool:
        """Start container with optimized settings."""
        self.container_name = f"android-fvm-optimized-{int(time.time())}"
        self.log_step(f"Starting optimized container: {self.container_name}")
        
        try:
            docker_args = [
                "docker", "run", "-d", 
                "--name", self.container_name,
                "--tmpfs", f"/tmp:rw,exec,nosuid,size={CONTAINER_CONFIG['tmpfs_size']}",
                "--env", "DEBIAN_FRONTEND=noninteractive",
                self.image_name, 
                "sleep", "7200"  # 2 hours
            ]
            
            result = subprocess.run(
                docker_args,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                self.log_error(f"Failed to start container: {result.stderr}")
                return False
                
            self.container_id = result.stdout.strip()
            self.log_success(f"Container started: {self.container_id[:12]}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start container: {e}")
            return False
    
    def run_container_command(self, command: str, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run command in container."""
        if not self.container_id:
            raise RuntimeError("No container available")
            
        docker_cmd = [
            "docker", "exec", 
            self.container_id,
            "bash", "-c", command
        ]
        
        return subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    
    def optimize_container_space(self) -> bool:
        """Run space optimization in container."""
        self.log_step("Optimizing container space...")
        
        # Copy optimization script to container
        copy_result = subprocess.run([
            "docker", "cp",
            str(OPTIMIZATION_SCRIPT),
            f"{self.container_id}:/tmp/optimize_docker_space.sh"
        ], capture_output=True)
        
        if copy_result.returncode != 0:
            self.log_error("Failed to copy optimization script")
            return False
        
        # Run optimization
        result = self.run_container_command(
            "chmod +x /tmp/optimize_docker_space.sh && sudo /tmp/optimize_docker_space.sh",
            timeout=180
        )
        
        if result.returncode == 0:
            self.log_success("Container space optimized")
            logger.info(f"Optimization output:\n{result.stdout}")
            return True
        else:
            self.log_error(f"Space optimization failed: {result.stderr}")
            return False
    
    def run_installation(self) -> bool:
        """Run the installation script with optimizations."""
        self.log_step("Running installation with optimizations...")
        
        # Copy install script
        copy_result = subprocess.run([
            "docker", "cp",
            str(INSTALL_SCRIPT),
            f"{self.container_id}:/home/testuser/install.sh"
        ], capture_output=True)
        
        if copy_result.returncode != 0:
            self.log_error("Failed to copy install script")
            return False
        
        # Make executable and run
        install_command = """
        cd /home/testuser &&
        chmod +x install.sh &&
        sudo chown testuser:testuser install.sh &&
        ./install.sh --debug --allow-root
        """
        
        result = self.run_container_command(install_command, timeout=900)  # 15 minutes
        
        if result.returncode == 0:
            self.log_success("Installation completed successfully")
            return True
        else:
            self.log_error(f"Installation failed: {result.stderr}")
            logger.info(f"Installation output:\n{result.stdout}")
            return False
    
    def run_verification(self) -> bool:
        """Run installation verification."""
        self.log_step("Running installation verification...")
        
        # Copy verification script
        copy_result = subprocess.run([
            "docker", "cp",
            str(VERIFICATION_SCRIPT),
            f"{self.container_id}:/home/testuser/verify_installation.py"
        ], capture_output=True)
        
        if copy_result.returncode != 0:
            self.log_error("Failed to copy verification script")
            return False
        
        # Run verification
        verify_command = """
        cd /home/testuser &&
        chmod +x verify_installation.py &&
        python3 verify_installation.py
        """
        
        result = self.run_container_command(verify_command, timeout=120)
        
        logger.info(f"Verification output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Verification stderr:\n{result.stderr}")
        
        if result.returncode == 0:
            self.log_success("All verification checks passed!")
            return True
        else:
            self.log_error("Verification checks failed")
            return False
    
    def test_android_sdk_location(self) -> bool:
        """Test Android SDK installation at expected location."""
        self.log_step("Testing Android SDK location...")
        
        # Check if Android SDK exists at expected location
        result = self.run_container_command(
            "test -f /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager && echo 'SDK_FOUND' || echo 'SDK_NOT_FOUND'"
        )
        
        if result.returncode == 0 and "SDK_FOUND" in result.stdout:
            self.log_success("Android SDK found at /opt/android-sdk")
            
            # Test sdkmanager functionality
            sdk_test = self.run_container_command(
                "/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --list_installed",
                timeout=60
            )
            
            if sdk_test.returncode == 0:
                self.log_success("Android SDK sdkmanager is functional")
                return True
            else:
                self.log_error("Android SDK sdkmanager failed")
                return False
        else:
            self.log_error("Android SDK not found at expected location")
            return False
    
    def test_fvm_location(self) -> bool:
        """Test FVM installation and functionality."""
        self.log_step("Testing FVM location and functionality...")
        
        # Check if FVM is available
        result = self.run_container_command("which fvm || echo 'FVM_NOT_IN_PATH'")
        
        if "FVM_NOT_IN_PATH" not in result.stdout:
            fvm_path = result.stdout.strip()
            self.log_success(f"FVM found in PATH: {fvm_path}")
        else:
            # Check common locations
            common_locations = [
                "/home/testuser/.pub-cache/bin/fvm",
                "/opt/pub-cache/bin/fvm",
                "/usr/local/bin/fvm"
            ]
            
            fvm_found = False
            for location in common_locations:
                check_result = self.run_container_command(f"test -f {location} && echo 'FOUND' || echo 'NOT_FOUND'")
                if "FOUND" in check_result.stdout:
                    self.log_success(f"FVM found at {location}")
                    fvm_found = True
                    break
            
            if not fvm_found:
                self.log_error("FVM not found in any expected location")
                return False
        
        # Test FVM functionality
        fvm_test = self.run_container_command("fvm --version", timeout=30)
        if fvm_test.returncode == 0:
            self.log_success(f"FVM is functional: {fvm_test.stdout.strip()}")
            return True
        else:
            self.log_error(f"FVM functionality test failed: {fvm_test.stderr}")
            return False
    
    def cleanup(self):
        """Clean up container."""
        if self.container_id:
            self.log_step(f"Cleaning up container: {self.container_id[:12]}")
            subprocess.run(
                ["docker", "rm", "-f", self.container_id], 
                capture_output=True
            )
    
    def run_all_tests(self) -> bool:
        """Run all optimized tests."""
        success = True
        
        try:
            if console:
                console.print("\n[bold cyan]🚀 Komodo Codex Environment - Optimized Android & FVM Tests[/bold cyan]")
                console.print("=" * 70)
            
            # Check prerequisites
            if not self.check_docker_available():
                return False
            
            # Build image
            if not self.build_optimized_image():
                return False
            
            # Start container
            if not self.start_optimized_container():
                return False
            
            # Optimize container space
            if not self.optimize_container_space():
                success = False
            
            # Run installation
            if success and not self.run_installation():
                success = False
            
            # Run verification
            if success and not self.run_verification():
                success = False
            
            # Test Android SDK
            if success and not self.test_android_sdk_location():
                success = False
            
            # Test FVM
            if success and not self.test_fvm_location():
                success = False
            
            # Final status
            if success:
                self.log_success("🎉 All tests passed successfully!")
            else:
                self.log_error("❌ Some tests failed. Check the logs above.")
            
            return success
            
        except KeyboardInterrupt:
            self.log_error("Tests interrupted by user")
            return False
        except Exception as e:
            self.log_error(f"Unexpected error: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    test_runner = OptimizedAndroidFVMTest()
    success = test_runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
