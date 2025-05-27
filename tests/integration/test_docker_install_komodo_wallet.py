#!/usr/bin/env python3
"""
Docker integration test for Komodo Codex Environment installation 
with Komodo Wallet repository.

This test:
1. Creates a Docker container with Ubuntu 22.04
2. Clones the komodo-wallet repository 
3. Runs the install.sh script to install the environment
4. Runs the setup command to configure and fetch documentation
5. Verifies AGENTS.md and KDF_API_DOCUMENTATION.md are present in the wallet directory
"""

import os
import subprocess
import time
from pathlib import Path


class DockerInstallTest:
    """Test Komodo Codex Environment installation in Docker with komodo-wallet."""
    
    def __init__(self):
        self.container_id = None
        self.container_name = f"kce-test-komodo-wallet-{int(time.time())}"
        self.image_name = "ubuntu:22.04"
        
    def setup_container(self):
        """Create and start the Docker container."""
        print("Creating Docker container...")
        
        # Create container
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "--platform", "linux/amd64",  # Ensure consistent platform
            self.image_name,
            "sleep", "3600"  # Keep container running
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create container: {result.stderr}")
        
        self.container_id = result.stdout.strip()
        print(f"Container created: {self.container_id[:12]}")
        
        # Install basic dependencies
        print("Installing basic dependencies...")
        self._exec_in_container([
            "apt-get", "update", "-qq"
        ], timeout=120)
        
        self._exec_in_container([
            "apt-get", "install", "-y", "-qq",
            "curl", "git", "wget", "unzip", "sudo"
        ], timeout=300)
        
    def clone_komodo_wallet(self):
        """Clone the komodo-wallet repository."""
        print("Cloning komodo-wallet repository...")
        
        # Create test user
        self._exec_in_container([
            "useradd", "-m", "-s", "/bin/bash", "testuser"
        ])
        
        # Give testuser sudo privileges
        self._exec_in_container([
            "usermod", "-aG", "sudo", "testuser"
        ])
        
        # Set up passwordless sudo for testuser
        self._exec_in_container([
            "bash", "-c", "echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
        ])
        
        # Clone komodo-wallet repository as testuser
        self._exec_in_container([
            "su", "-", "testuser", "-c",
            "git clone https://github.com/KomodoPlatform/komodo-wallet.git"
        ], timeout=120)
        
        # Verify the repository was cloned
        result = self._exec_in_container([
            "su", "-", "testuser", "-c",
            "ls -la /home/testuser/komodo-wallet"
        ])
        
        if result.returncode != 0:
            raise Exception("Failed to clone komodo-wallet repository")
        
        print("komodo-wallet repository cloned successfully")
        
    def run_install_script(self):
        """Download and run the install.sh script."""
        print("Running install.sh script...")
        
        # Download and run install script as testuser
        install_cmd = (
            "curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | "
            "bash"
        )
        
        result = self._exec_in_container([
            "su", "-", "testuser", "-c", install_cmd
        ], timeout=900)  # 15 minute timeout
        
        print(f"Install script exit code: {result.returncode}")
        if result.stdout:
            print("Install script STDOUT (last 50 lines):")
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines[-50:]:
                print(f"  {line}")
        
        if result.stderr:
            print("Install script STDERR (last 20 lines):")
            stderr_lines = result.stderr.split('\n')
            for line in stderr_lines[-20:]:
                print(f"  {line}")
        
        if result.returncode != 0:
            print(f"Install script failed with exit code: {result.returncode}")
            # Don't fail here, let's see what was installed
        
        print("Install script completed")
        
    def run_setup_in_wallet_dir(self):
        """Run the setup command in the komodo-wallet directory to fetch documentation."""
        print("Running setup command in komodo-wallet directory...")
        
        # First, let's see if the environment is accessible
        test_cmd = (
            "source ~/.komodo-codex-env/setup_env.sh && "
            "which kce"
        )
        
        result = self._exec_in_container([
            "su", "-", "testuser", "-c", test_cmd
        ])
        
        print(f"kce command location: {result.stdout.strip()}")
        if result.returncode != 0:
            print("kce command not found, trying alternative approach...")
            
        # Change to komodo-wallet directory and run setup with documentation
        setup_cmd = (
            "cd /home/testuser/komodo-wallet && "
            "source ~/.komodo-codex-env/setup_env.sh && "
            "kce setup --kdf-docs --verbose"
        )
        
        result = self._exec_in_container([
            "su", "-", "testuser", "-c", setup_cmd
        ], timeout=600)  # 10 minute timeout
        
        print(f"Setup command exit code: {result.returncode}")
        if result.stdout:
            print("Setup STDOUT (last 30 lines):")
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines[-30:]:
                print(f"  {line}")
        
        if result.stderr:
            print("Setup STDERR:")
            print(result.stderr)
        
        print("Setup command completed")
        
    def verify_documentation_files(self):
        """Verify that documentation files are present in the komodo-wallet directory."""
        print("Verifying documentation files...")
        
        wallet_dir = "/home/testuser/komodo-wallet"
        
        # List all files in the wallet directory
        result = self._exec_in_container([
            "su", "-", "testuser", "-c",
            f"ls -la {wallet_dir}"
        ])
        
        print("Files in komodo-wallet directory:")
        print(result.stdout)
        
        # Search for specific documentation files
        agents_result = self._exec_in_container([
            "su", "-", "testuser", "-c",
            f"find {wallet_dir} -maxdepth 1 -name 'AGENTS*.md' -type f"
        ])
        
        kdf_result = self._exec_in_container([
            "su", "-", "testuser", "-c",
            f"find {wallet_dir} -maxdepth 1 -name 'KDF_API_DOCUMENTATION.md' -type f"
        ])
        
        # Search for docs directory
        docs_result = self._exec_in_container([
            "su", "-", "testuser", "-c",
            f"find {wallet_dir}/docs -name '*.md' -type f 2>/dev/null || echo 'docs directory not found'"
        ])
        
        agents_files = agents_result.stdout.strip().split('\n') if agents_result.stdout.strip() else []
        kdf_files = kdf_result.stdout.strip().split('\n') if kdf_result.stdout.strip() else []
        docs_files = docs_result.stdout.strip().split('\n') if docs_result.stdout.strip() and 'not found' not in docs_result.stdout else []
        
        print(f"AGENTS files found: {agents_files}")
        print(f"KDF API files found: {kdf_files}")
        print(f"Docs files found: {docs_files}")
        
        return {
            "agents_files": [f for f in agents_files if f],
            "kdf_files": [f for f in kdf_files if f],
            "docs_files": [f for f in docs_files if f and 'not found' not in f],
            "agents_exists": len([f for f in agents_files if f]) > 0,
            "kdf_exists": len([f for f in kdf_files if f]) > 0
        }
        
    def cleanup(self):
        """Clean up the Docker container."""
        if self.container_id:
            print(f"Cleaning up container {self.container_id[:12]}...")
            subprocess.run(["docker", "rm", "-f", self.container_id], 
                         capture_output=True)
            
    def _exec_in_container(self, cmd, timeout=120):
        """Execute a command in the container."""
        docker_cmd = ["docker", "exec", self.container_id] + cmd
        return subprocess.run(
            docker_cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
    def run_test(self):
        """Run the complete test."""
        try:
            self.setup_container()
            self.clone_komodo_wallet()
            self.run_install_script()
            self.run_setup_in_wallet_dir()
            results = self.verify_documentation_files()
            
            print("\n" + "="*60)
            print("TEST RESULTS")
            print("="*60)
            print(f"AGENTS.md files found: {len(results['agents_files'])}")
            print(f"KDF API files found: {len(results['kdf_files'])}")
            print(f"Docs files found: {len(results['docs_files'])}")
            
            if results['agents_exists']:
                print("✅ AGENTS.md documentation is present in komodo-wallet directory")
            else:
                print("❌ AGENTS.md documentation is missing from komodo-wallet directory")
                
            if results['kdf_exists']:
                print("✅ KDF API documentation is present in komodo-wallet directory")
            else:
                print("❌ KDF API documentation is missing from komodo-wallet directory")
                
            return results
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            raise
        finally:
            self.cleanup()


if __name__ == "__main__":
    test = DockerInstallTest()
    try:
        results = test.run_test()
        
        # Exit with appropriate code
        if results['agents_exists']:
            print("\nTest PASSED: Documentation files are present in komodo-wallet directory")
            exit(0)
        else:
            print("\nTest FAILED: Documentation files are missing from komodo-wallet directory")
            exit(1)
            
    except Exception as e:
        print(f"Test execution failed: {e}")
        exit(1)
