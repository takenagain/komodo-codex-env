#!/usr/bin/env python3
"""Docker-based test for the install script."""

import subprocess
import sys
import time
import unittest
from pathlib import Path


class DockerInstallTest(unittest.TestCase):
    """Test the install script using Docker containers."""
    
    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.container_ids = []
        
        # Check if Docker is available
        try:
            subprocess.run(['docker', '--version'], 
                         check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("Docker is not available")
    
    def tearDown(self):
        """Clean up Docker containers."""
        for container_id in self.container_ids:
            try:
                subprocess.run(['docker', 'rm', '-f', container_id], 
                             capture_output=True)
            except subprocess.CalledProcessError:
                pass
    
    def _build_test_image(self):
        """Build the test Docker image."""
        dockerfile_path = self.project_root / '.devcontainer' / 'Dockerfile'
        
        result = subprocess.run([
            'docker', 'build', 
            '-t', 'komodo-codex-env-test',
            '-f', str(dockerfile_path),
            str(self.project_root)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            self.fail(f"Failed to build Docker image: {result.stderr}")
        
        return True
    
    def _start_container(self):
        """Start a test container."""
        result = subprocess.run([
            'docker', 'run', '-d',
            '--name', f'komodo-test-{int(time.time())}',
            'komodo-codex-env-test',
            'sleep', '3600'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            self.fail(f"Failed to start container: {result.stderr}")
        
        container_id = result.stdout.strip()
        self.container_ids.append(container_id)
        return container_id
    
    def _copy_install_script(self, container_id):
        """Copy install script to container."""
        install_script = self.project_root / 'install.sh'
        
        result = subprocess.run([
            'docker', 'cp',
            str(install_script),
            f'{container_id}:/tmp/install.sh'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            self.fail(f"Failed to copy install script: {result.stderr}")
    
    def _run_install_script(self, container_id, user='testuser', extra_args=''):
        """Run the install script in the container."""
        if user == 'testuser':
            home_dir = '/home/testuser'
        else:
            home_dir = '/root'
        
        cmd = [
            'docker', 'exec', '-u', user, container_id,
            'bash', '-c',
            f'cd {home_dir} && bash /tmp/install.sh --debug {extra_args}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return result
    
    def _verify_installation(self, container_id, user='testuser'):
        """Verify the installation was successful."""
        if user == 'testuser':
            home_dir = '/home/testuser'
        else:
            home_dir = '/root'
        
        cmd = [
            'docker', 'exec', '-u', user, container_id,
            'bash', '-c',
            f'cd {home_dir}/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def test_basic_install_non_root(self):
        """Test basic installation with non-root user."""
        print("\n=== Testing basic installation (non-root) ===")
        
        # Build image
        self._build_test_image()
        
        # Start container
        container_id = self._start_container()
        
        # Copy install script
        self._copy_install_script(container_id)
        
        # Run install script
        result = self._run_install_script(container_id, user='testuser')
        
        if result.returncode != 0:
            print(f"Install script failed with return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            self.fail("Install script failed for non-root user")
        
        # Verify installation
        if not self._verify_installation(container_id, user='testuser'):
            self.fail("Installation verification failed for non-root user")
        
        print("✓ Non-root installation successful")
    
    def test_root_install(self):
        """Test installation with root user."""
        print("\n=== Testing root installation ===")
        
        # Build image
        self._build_test_image()
        
        # Start container
        container_id = self._start_container()
        
        # Copy install script
        self._copy_install_script(container_id)
        
        # Run install script as root
        result = self._run_install_script(container_id, user='root', extra_args='--allow-root')
        
        if result.returncode != 0:
            print(f"Install script failed with return code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            self.fail("Install script failed for root user")
        
        # Verify installation
        if not self._verify_installation(container_id, user='root'):
            self.fail("Installation verification failed for root user")
        
        print("✓ Root installation successful")
    
    def test_uv_entry_point_availability(self):
        """Test that UV entry points are properly installed."""
        print("\n=== Testing UV entry point installation ===")
        
        # Build image
        self._build_test_image()
        
        # Start container
        container_id = self._start_container()
        
        # Copy install script
        self._copy_install_script(container_id)
        
        # Run install script
        result = self._run_install_script(container_id, user='testuser')
        
        if result.returncode != 0:
            self.fail("Install script failed")
        
        # Test UV entry point
        cmd = [
            'docker', 'exec', '-u', 'testuser', container_id,
            'bash', '-c',
            'cd /home/testuser/.komodo-codex-env && export PATH="$HOME/.local/bin:$PATH" && uv run komodo-codex-env --version'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"UV entry point test failed: {result.stderr}")
            self.fail("UV entry point not working properly")
        
        print("✓ UV entry point working correctly")


if __name__ == '__main__':
    unittest.main(verbosity=2)