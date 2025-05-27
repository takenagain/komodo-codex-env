#!/usr/bin/env python3
"""
Installation verification script for Komodo Codex Environment.

This script verifies that all required components are properly installed:
- Android SDK at /opt/android-sdk
- FVM (Flutter Version Management) 
- Required tools and environment variables
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class InstallationVerifier:
    """Verifies Komodo Codex Environment installation."""
    
    def __init__(self):
        self.issues = []
        self.successes = []
        
    def log_success(self, message: str):
        """Log a successful verification."""
        print(f"✓ {message}")
        self.successes.append(message)
        
    def log_issue(self, message: str):
        """Log an issue found during verification."""
        print(f"✗ {message}")
        self.issues.append(message)
        
    def log_info(self, message: str):
        """Log informational message."""
        print(f"ℹ {message}")
        
    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command, 
                capture_output=capture_output, 
                text=True, 
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except FileNotFoundError:
            return 1, "", f"Command not found: {command[0]}"
    
    def check_android_sdk(self) -> bool:
        """Verify Android SDK installation."""
        self.log_info("Checking Android SDK installation...")
        
        android_home = os.environ.get("ANDROID_HOME", "/opt/android-sdk")
        android_sdk_root = os.environ.get("ANDROID_SDK_ROOT", "/opt/android-sdk")
        
        # Check environment variables
        if android_home != android_sdk_root:
            self.log_issue(f"ANDROID_HOME ({android_home}) != ANDROID_SDK_ROOT ({android_sdk_root})")
            return False
            
        # Check SDK directory exists
        sdk_path = Path(android_home)
        if not sdk_path.exists():
            self.log_issue(f"Android SDK directory not found: {android_home}")
            return False
            
        # Check essential SDK components
        essential_paths = [
            "cmdline-tools/latest/bin/sdkmanager",
            "platform-tools/adb",
        ]
        
        missing_components = []
        for component in essential_paths:
            component_path = sdk_path / component
            if not component_path.exists():
                missing_components.append(str(component_path))
                
        if missing_components:
            self.log_issue(f"Missing Android SDK components: {', '.join(missing_components)}")
            return False
            
        # Test sdkmanager
        sdkmanager_path = sdk_path / "cmdline-tools/latest/bin/sdkmanager"
        if sdkmanager_path.exists():
            exit_code, stdout, stderr = self.run_command([str(sdkmanager_path), "--list_installed"])
            if exit_code != 0:
                self.log_issue(f"sdkmanager failed: {stderr}")
                return False
            else:
                self.log_success(f"Android SDK verified at {android_home}")
                return True
        
        return False
    
    def check_fvm(self) -> bool:
        """Verify FVM installation."""
        self.log_info("Checking FVM installation...")
        
        # Check if FVM is in PATH
        exit_code, stdout, stderr = self.run_command(["which", "fvm"])
        if exit_code != 0:
            # Check common installation locations
            common_paths = [
                Path.home() / ".pub-cache/bin/fvm",
                Path("/usr/local/bin/fvm"),
                Path("/opt/pub-cache/bin/fvm")
            ]
            
            fvm_found = False
            for fvm_path in common_paths:
                if fvm_path.exists():
                    self.log_success(f"FVM found at {fvm_path}")
                    fvm_found = True
                    break
                    
            if not fvm_found:
                self.log_issue("FVM not found in PATH or common locations")
                return False
        else:
            fvm_path = stdout.strip()
            self.log_success(f"FVM found in PATH: {fvm_path}")
            
        # Test FVM functionality
        exit_code, stdout, stderr = self.run_command(["fvm", "--version"])
        if exit_code != 0:
            self.log_issue(f"FVM command failed: {stderr}")
            return False
        else:
            version = stdout.strip()
            self.log_success(f"FVM version: {version}")
            return True
    
    def check_dart(self) -> bool:
        """Verify Dart SDK installation."""
        self.log_info("Checking Dart SDK installation...")
        
        exit_code, stdout, stderr = self.run_command(["dart", "--version"])
        if exit_code != 0:
            self.log_issue(f"Dart not found or failed: {stderr}")
            return False
        else:
            version_line = stderr.split('\n')[0] if stderr else stdout.split('\n')[0]
            self.log_success(f"Dart SDK: {version_line}")
            return True
    
    def check_java(self) -> bool:
        """Verify Java installation for Android development."""
        self.log_info("Checking Java installation...")
        
        exit_code, stdout, stderr = self.run_command(["java", "-version"])
        if exit_code != 0:
            self.log_issue(f"Java not found: {stderr}")
            return False
        else:
            version_line = stderr.split('\n')[0] if stderr else stdout.split('\n')[0]
            self.log_success(f"Java: {version_line}")
            return True
    
    def check_environment_variables(self) -> bool:
        """Verify required environment variables."""
        self.log_info("Checking environment variables...")
        
        required_vars = {
            "ANDROID_HOME": "/opt/android-sdk",
            "ANDROID_SDK_ROOT": "/opt/android-sdk",
        }
        
        optional_vars = {
            "FLUTTER_ROOT": "/opt/flutter",
            "PUB_CACHE": "/opt/pub-cache",
        }
        
        all_good = True
        
        for var, expected in required_vars.items():
            actual = os.environ.get(var)
            if not actual:
                self.log_issue(f"Required environment variable {var} not set")
                all_good = False
            elif actual != expected:
                self.log_issue(f"{var} = {actual}, expected {expected}")
                all_good = False
            else:
                self.log_success(f"{var} = {actual}")
        
        for var, expected in optional_vars.items():
            actual = os.environ.get(var)
            if actual:
                self.log_success(f"{var} = {actual}")
            else:
                self.log_info(f"{var} not set (optional)")
                
        return all_good
    
    def check_disk_space(self) -> bool:
        """Check available disk space."""
        self.log_info("Checking disk space...")
        
        exit_code, stdout, stderr = self.run_command(["df", "-h", "/"])
        if exit_code != 0:
            self.log_issue(f"Failed to check disk space: {stderr}")
            return False
        
        lines = stdout.strip().split('\n')
        if len(lines) >= 2:
            header = lines[0]
            data = lines[1]
            self.log_success(f"Disk space: {data}")
            
            # Extract available space (4th column)
            parts = data.split()
            if len(parts) >= 4:
                available = parts[3]
                # Simple check for very low space (less than 1G)
                if available.endswith('M') or (available.endswith('G') and float(available[:-1]) < 1):
                    self.log_issue(f"Low disk space: {available} available")
                    return False
                    
        return True
    
    def run_verification(self) -> bool:
        """Run all verification checks."""
        print("🔍 Komodo Codex Environment Installation Verification")
        print("=" * 60)
        
        checks = [
            ("Disk Space", self.check_disk_space),
            ("Environment Variables", self.check_environment_variables),
            ("Java JDK", self.check_java),
            ("Dart SDK", self.check_dart),
            ("Android SDK", self.check_android_sdk),
            ("FVM", self.check_fvm),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"\n--- {check_name} ---")
            try:
                result = check_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.log_issue(f"Check failed with exception: {e}")
                all_passed = False
        
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        
        if self.successes:
            print(f"✅ Passed checks ({len(self.successes)}):")
            for success in self.successes:
                print(f"   ✓ {success}")
        
        if self.issues:
            print(f"\n❌ Failed checks ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   ✗ {issue}")
        
        if all_passed:
            print("\n🎉 All verification checks passed!")
            return True
        else:
            print(f"\n⚠️  {len(self.issues)} issue(s) found. Please fix them before proceeding.")
            return False


def main():
    """Main entry point."""
    verifier = InstallationVerifier()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
