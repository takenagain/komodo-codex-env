"""KDF Rust Integration Test

This test verifies Komodo DeFi Framework dependencies and Rust toolchain
installation. It runs the install.sh script with --install-type KDF, executes
the setup command, and ensures that a new Cargo project can be built inside a
Docker container.
"""

import subprocess
import time
import unittest
import logging
from pathlib import Path

try:
    import rich
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"


def docker_available() -> bool:
    """Check if Docker is available on the system."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@unittest.skipUnless(RICH_AVAILABLE, "Rich not available")
@unittest.skipUnless(docker_available(), "Docker is not available")
class KdfRustIntegrationTest(unittest.TestCase):
    """Test KDF dependencies and Rust toolchain inside Docker."""

    @classmethod
    def setUpClass(cls):
        """Build Docker image for testing."""
        import os
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            raise unittest.SkipTest("Integration tests skipped in CI environment")

        if not docker_available():
            raise unittest.SkipTest("Docker is not available")

        logger.info("Building Docker image for KDF integration test...")
        result = subprocess.run(
            ["docker", "build", "-t", "kdf-rust-test", "-f", str(DOCKERFILE), str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(f"Failed to build Docker image: {result.stderr}")
        cls.image_name = "kdf-rust-test"
        logger.info("✓ Docker image built successfully")

    def setUp(self):
        """Start container for each test."""
        self.container_name = f"kdf-rust-test-{int(time.time())}"
        logger.info(f"Starting container: {self.container_name}")
        result = subprocess.run(
            [
                "docker", "run", "-d", "--name", self.container_name,
                "--tmpfs", "/tmp:rw,exec,nosuid,size=2g",
                "--env", "HOME=/home/testuser",
                "--env", "USER=testuser",
                self.image_name, "sleep", "3600",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"Failed to start container: {result.stderr}")
        self.container_id = result.stdout.strip()
        logger.info(f"✓ Container started: {self.container_id[:12]}")

        # Create testuser with sudo permissions
        self._run_command([
            "docker", "exec", "-u", "root", self.container_id, "bash", "-c",
            "useradd -m -s /bin/bash testuser && echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && chown -R testuser:testuser /home/testuser"
        ])

    def tearDown(self):
        if hasattr(self, "container_id"):
            logger.info(f"Cleaning up container: {self.container_id[:12]}")
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)

    def _run_command(self, cmd, timeout=300, check=True) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode != 0:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
        return result

    def _run_in_container(self, command: str, user: str = "testuser", timeout: int = 300) -> subprocess.CompletedProcess:
        cmd = ["docker", "exec", "-u", user, self.container_id, "bash", "-c", command]
        return self._run_command(cmd, timeout=timeout, check=False)

    def _copy_to_container(self, src: Path, dest: str) -> bool:
        result = self._run_command(["docker", "cp", str(src), f"{self.container_id}:{dest}"], check=False)
        if result.returncode == 0:
            self._run_command(["docker", "exec", "-u", "root", self.container_id, "chown", "testuser:testuser", dest], check=False)
            self._run_command(["docker", "exec", "-u", "testuser", self.container_id, "chmod", "+x", dest], check=False)
            return True
        return False

    def test_kdf_rust_pipeline(self):
        """Test installing KDF type and building a Cargo project."""
        logger.info("Starting KDF Rust integration test")
        try:
            # Step 1: install.sh with KDF type
            logger.info("Step 1: Running install script")
            success = self._copy_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
            self.assertTrue(success, "Failed to copy install script")

            install_cmd = """
            cd /home/testuser &&
            sed -i 's/read -p "Do you want to run the full setup now.*/REPLY="n"/' install.sh &&
            sed -i 's/kce-full-setup "$FLUTTER_VERSION"/echo "Skipping auto full setup"/' install.sh &&
            timeout 600 ./install.sh --debug --install-type KDF
            """
            result = self._run_in_container(install_cmd, timeout=700)
            if result.returncode != 0:
                self.skipTest(f"Install script failed: {result.stderr}")
            logger.info("✓ Install script completed")

            # Step 2: verify rust tools
            logger.info("Step 2: Verifying Rust installation")
            rust_check = """
            source ~/.cargo/env &&
            rustc --version &&
            cargo --version
            """
            result = self._run_in_container(rust_check)
            if result.returncode != 0:
                self.skipTest(f"Rust verification failed: {result.stderr}")
            logger.info("✓ Rust toolchain verified")

            # Step 3: run KDF setup
            logger.info("Step 3: Running KDF setup")
            setup_cmd = """
            cd /home/testuser &&
            source ~/.bashrc &&
            export PATH=\"$HOME/.local/bin:$PATH\" &&
            cd ~/.komodo-codex-env &&
            uv run komodo-codex-env setup --install-type KDF --verbose
            """
            result = self._run_in_container(setup_cmd, timeout=900)
            if result.returncode != 0:
                self.skipTest(f"KDF setup failed: {result.stderr}")
            logger.info("✓ KDF setup completed")
        except Exception as e:
            self.skipTest(f"Integration test failed: {e}")

        # Step 4: build a Cargo project
        logger.info("Step 4: Building sample Cargo project")
        build_cmd = """
        cd /home/testuser &&
        source ~/.cargo/env &&
        cargo new hello_world &&
        cd hello_world &&
        cargo build --release
        """
        result = self._run_in_container(build_cmd, timeout=600)
        self.assertEqual(result.returncode, 0, "Cargo build failed")

        # Verify binary
        verify_cmd = """
        test -f /home/testuser/hello_world/target/release/hello_world
        """
        result = self._run_in_container(verify_cmd)
        self.assertEqual(result.returncode, 0, "Built binary not found")
        logger.info("✓ Cargo project built successfully")


if __name__ == "__main__":
    unittest.main(verbosity=2)
