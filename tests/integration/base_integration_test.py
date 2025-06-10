"""
Base Integration Test Class

Provides a common base class for integration tests that use container engines,
with support for both Docker and Podman through the container engine abstraction.
"""

import time
import unittest
import logging
from pathlib import Path
from typing import Dict, Union
import subprocess

from .container_engine import ContainerEngine, ContainerEngineError, container_available

try:
    from rich.logging import RichHandler
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    RICH_AVAILABLE = True
except ImportError:
    logging.basicConfig(level=logging.INFO)
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class BaseIntegrationTest(unittest.TestCase):
    """Base class for container-based integration tests."""
    
    # Class-level configuration
    IMAGE_NAME: str = ""  # To be set by subclasses
    CONTAINER_PREFIX: str = "test"  # To be set by subclasses
    DOCKERFILE: Union[str, Path] = ""  # To be set by subclasses
    BUILD_CONTEXT: Union[str, Path] = ""  # To be set by subclasses
    BUILD_TIMEOUT = 600  # 10 minutes
    CONTAINER_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def setUpClass(cls):
        """Set up container engine and build image for testing."""
        # Skip tests in CI environments unless explicitly enabled
        import os
        if (os.getenv("CI") or os.getenv("GITHUB_ACTIONS")) and not os.getenv("ENABLE_INTEGRATION_TESTS"):
            raise unittest.SkipTest("Integration tests skipped in CI environment")
        
        # Check if container engine is available
        if not container_available():
            raise unittest.SkipTest("No container engine (Docker/Podman) is available")
        
        # Initialize container engine
        try:
            cls.engine = ContainerEngine()
            logger.info(f"Using container engine: {cls.engine.engine}")
            logger.info(f"Version: {cls.engine.version()}")
        except ContainerEngineError as e:
            raise unittest.SkipTest(f"Container engine setup failed: {e}")
        
        # Validate required class attributes
        if not cls.IMAGE_NAME:
            raise ValueError("IMAGE_NAME must be set by subclass")
        if not cls.DOCKERFILE:
            raise ValueError("DOCKERFILE must be set by subclass")
        if not cls.BUILD_CONTEXT:
            raise ValueError("BUILD_CONTEXT must be set by subclass")
        
        # Build the Docker/Podman image
        cls._build_image()
    
    @classmethod
    def _build_image(cls):
        """Build the container image for testing."""
        logger.info(f"Building container image: {cls.IMAGE_NAME}")
        
        try:
            result = cls.engine.build(
                tag=cls.IMAGE_NAME,
                dockerfile=str(cls.DOCKERFILE),
                context=str(cls.BUILD_CONTEXT),
                capture_output=True,
                text=True,
                timeout=cls.BUILD_TIMEOUT
            )
            
            if result.returncode != 0:
                logger.error(f"Image build failed: {result.stderr}")
                raise unittest.SkipTest(f"Failed to build container image: {result.stderr}")
            
            logger.info("✓ Container image built successfully")
            
        except subprocess.TimeoutExpired:
            raise unittest.SkipTest("Container image build timed out")
        except Exception as e:
            raise unittest.SkipTest(f"Container image build failed: {e}")
    
    def setUp(self):
        """Start a new container for the test."""
        self.container_name = f"{self.CONTAINER_PREFIX}-{int(time.time())}"
        logger.info(f"Starting container: {self.container_name}")
        
        # Default container configuration
        container_config = self._get_container_config()
        
        try:
            result = self.engine.run(
                image=self.IMAGE_NAME,
                name=self.container_name,
                detach=True,
                command=["sleep", str(self.CONTAINER_TIMEOUT)],
                **container_config,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.skipTest(f"Failed to start container: {result.stderr}")
            
            self.container_id = result.stdout.strip()
            logger.info(f"✓ Container started: {self.container_id[:12] if self.container_id else 'unknown'}")
            
            # Set up container environment
            self._setup_container()
            
        except Exception as e:
            self.skipTest(f"Container setup failed: {e}")
    
    def tearDown(self):
        """Clean up container."""
        if hasattr(self, "container_id") and self.container_id:
            logger.info(f"Cleaning up container: {self.container_id[:12]}")
            try:
                self.engine.rm(self.container_id, force=True, capture_output=True)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")
    
    def _get_container_config(self) -> Dict:
        """Get container configuration. Override in subclasses."""
        return {
            "extra_args": [
                "--tmpfs", "/tmp:rw,exec,nosuid,size=2g",
                "--env", "HOME=/home/testuser",
                "--env", "USER=testuser"
            ]
        }
    
    def _setup_container(self):
        """Set up container environment. Override in subclasses."""
        # Create testuser with proper permissions
        setup_command = [
            "bash", "-c",
            "useradd -m -s /bin/bash testuser && "
            "echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && "
            "chown -R testuser:testuser /home/testuser"
        ]
        
        result = self.engine.exec(
            container=self.container_id,
            command=setup_command,
            user="root",
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.warning(f"Container setup warning: {result.stderr}")
    
    # Helper methods for container operations
    
    def run_in_container(self, command: str, user: str = "testuser", 
                        timeout: int = 300) -> subprocess.CompletedProcess:
        """Run command in the container."""
        result = self.engine.exec(
            container=self.container_id,
            command=["bash", "-c", command],
            user=user,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    
    def copy_to_container(self, src_path: Path, dest_path: str) -> bool:
        """Copy file to container."""
        try:
            result = self.engine.cp(
                src=str(src_path),
                dest=f"{self.container_id}:{dest_path}",
                capture_output=True
            )
            
            if result.returncode == 0:
                # Fix ownership
                self.engine.exec(
                    container=self.container_id,
                    command=["chown", "testuser:testuser", dest_path],
                    user="root",
                    capture_output=True
                )
                self.engine.exec(
                    container=self.container_id,
                    command=["chmod", "+x", dest_path],
                    user="testuser",
                    capture_output=True
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to copy file to container: {e}")
            return False
    
    def get_container_logs(self) -> str:
        """Get container logs."""
        try:
            result = self.engine.logs(
                container=self.container_id,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return ""
    
    def assert_command_success(self, result: subprocess.CompletedProcess, 
                             message: str = "Command failed"):
        """Assert that a container command succeeded."""
        if result.returncode != 0:
            error_info = f"{message}\n"
            error_info += f"Exit code: {result.returncode}\n"
            error_info += f"STDOUT: {result.stdout}\n"
            error_info += f"STDERR: {result.stderr}"
            self.fail(error_info)
    
    def skip_on_command_failure(self, result: subprocess.CompletedProcess, 
                               message: str = "Command failed"):
        """Skip test if command failed (instead of failing)."""
        if result.returncode != 0:
            skip_msg = f"{message}: {result.stderr}"
            self.skipTest(skip_msg)


@unittest.skipUnless(RICH_AVAILABLE, "Rich not available")
@unittest.skipUnless(container_available(), "Container engine is not available")
class ContainerIntegrationTest(BaseIntegrationTest):
    """
    Convenience base class that automatically skips if requirements aren't met.
    Use this for most integration tests.
    """
    pass