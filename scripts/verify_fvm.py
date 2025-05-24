#!/usr/bin/env python3
"""
FVM Verification Script
Checks if FVM is properly installed and configured for both komodo and root users.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, user=None, capture_output=True):
    """Run a command, optionally as a different user."""
    if user and user != os.getenv('USER'):
        cmd = f"sudo -u {user} bash -c '{cmd}'"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        return None


def check_fvm_for_user(username):
    """Check if FVM is available for a specific user."""
    print(f"\n=== Checking FVM for user: {username} ===")
    
    # Get user home directory
    if username == "root":
        home_dir = "/root"
    else:
        home_dir = f"/home/{username}"
    
    # Check if user exists
    result = run_command(f"id {username}")
    if result is None or result.returncode != 0:
        print(f"❌ User {username} does not exist")
        return False
    
    print(f"✅ User {username} exists")
    
    # Check if FVM command is available
    result = run_command("command -v fvm", user=username)
    if result and result.returncode == 0:
        print(f"✅ FVM command found in PATH: {result.stdout.strip()}")
        fvm_available = True
    else:
        print("❌ FVM command not found in PATH")
        fvm_available = False
    
    # Check common FVM installation locations
    fvm_locations = [
        f"{home_dir}/.pub-cache/bin/fvm",
        f"{home_dir}/.fvm/fvm",
    ]
    
    found_locations = []
    for location in fvm_locations:
        if Path(location).exists():
            found_locations.append(location)
            print(f"✅ FVM binary found at: {location}")
    
    if not found_locations and not fvm_available:
        print("❌ FVM binary not found in any common locations")
    
    # Check pub-cache bin directory
    pub_cache_bin = f"{home_dir}/.pub-cache/bin"
    if Path(pub_cache_bin).exists():
        print(f"✅ Pub cache bin directory exists: {pub_cache_bin}")
        
        # List contents
        try:
            contents = list(Path(pub_cache_bin).iterdir())
            if contents:
                print(f"   Contents: {[f.name for f in contents]}")
            else:
                print("   Directory is empty")
        except Exception as e:
            print(f"   Could not list contents: {e}")
    else:
        print(f"❌ Pub cache bin directory does not exist: {pub_cache_bin}")
    
    # Check PATH configuration in shell profiles
    shell_profiles = [
        f"{home_dir}/.bashrc",
        f"{home_dir}/.zshrc",
        f"{home_dir}/.profile"
    ]
    
    path_configured = False
    for profile in shell_profiles:
        if Path(profile).exists():
            try:
                content = Path(profile).read_text()
                if ".pub-cache/bin" in content:
                    print(f"✅ PATH configured in {profile}")
                    path_configured = True
                    break
            except Exception as e:
                print(f"⚠️  Could not read {profile}: {e}")
    
    if not path_configured:
        print("❌ .pub-cache/bin not found in any shell profile")
    
    # Try to run FVM version
    result = run_command("fvm --version", user=username)
    if result and result.returncode == 0:
        print(f"✅ FVM version: {result.stdout.strip()}")
    else:
        print("❌ Could not get FVM version")
    
    # Check if Flutter is installed via FVM
    result = run_command("fvm list", user=username)
    if result and result.returncode == 0:
        if result.stdout.strip():
            print(f"✅ Flutter versions installed via FVM:")
            for line in result.stdout.strip().split('\n'):
                print(f"   {line}")
        else:
            print("⚠️  No Flutter versions installed via FVM")
    else:
        print("❌ Could not list FVM Flutter versions")
    
    return fvm_available or found_locations


def main():
    """Main verification function."""
    print("FVM Installation Verification")
    print("=" * 40)
    
    # Check current user
    current_user = os.getenv('USER', 'unknown')
    print(f"Running as user: {current_user}")
    
    success = True
    
    # Check for current user
    if not check_fvm_for_user(current_user):
        success = False
    
    # Check for komodo user if it exists
    result = run_command("id komodo")
    if result and result.returncode == 0:
        if not check_fvm_for_user("komodo"):
            success = False
    else:
        print("\n⚠️  Komodo user does not exist - skipping")
    
    # Check for root user if running with sudo privileges
    if os.geteuid() == 0 or subprocess.run("sudo -n true", shell=True, capture_output=True).returncode == 0:
        if not check_fvm_for_user("root"):
            success = False
    else:
        print("\n⚠️  No sudo privileges - skipping root user check")
    
    # Final summary
    print("\n" + "=" * 40)
    if success:
        print("✅ FVM verification completed successfully!")
        print("FVM appears to be properly configured for all checked users.")
    else:
        print("❌ FVM verification found issues!")
        print("FVM may not be properly configured for all users.")
        print("\nTo fix issues:")
        print("1. Run the install script: ./install.sh")
        print("2. Run setup: komodo-codex-env setup")
        print("3. Source your shell profile or restart your terminal")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())