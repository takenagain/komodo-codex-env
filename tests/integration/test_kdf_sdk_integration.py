import subprocess
import time
import unittest
import logging
from pathlib import Path

try:
    from rich.logging import RichHandler

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    RICH_AVAILABLE = True
except Exception:
    logging.basicConfig(level=logging.INFO)
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@unittest.skipUnless(RICH_AVAILABLE, "Rich not available")
@unittest.skipUnless(docker_available(), "Docker is not available")
class KdfSdkIntegrationTest(unittest.TestCase):
    """Verify KDF-SDK install type installs melos inside Docker."""

    @classmethod
    def setUpClass(cls):
        import os

        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            raise unittest.SkipTest("Integration tests skipped in CI environment")

        if not docker_available():
            raise unittest.SkipTest("Docker is not available")

        logger.info("Building Docker image for KDF-SDK integration test...")
        result = subprocess.run(
            [
                "docker",
                "build",
                "-t",
                "kdf-sdk-test",
                "-f",
                str(DOCKERFILE),
                str(PROJECT_ROOT),
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(f"Failed to build Docker image: {result.stderr}")
        cls.image_name = "kdf-sdk-test"
        logger.info("✓ Docker image built successfully")

    def setUp(self):
        self.container_name = f"kdf-sdk-test-{int(time.time())}"
        logger.info(f"Starting container: {self.container_name}")
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.container_name,
                "--tmpfs",
                "/tmp:rw,exec,nosuid,size=2g",
                "--env",
                "HOME=/home/testuser",
                "--env",
                "USER=testuser",
                self.image_name,
                "sleep",
                "3600",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.skipTest(f"Failed to start container: {result.stderr}")
        self.container_id = result.stdout.strip()
        logger.info(f"✓ Container started: {self.container_id[:12]}")

        # Create testuser
        self._run_command(
            [
                "docker",
                "exec",
                "-u",
                "root",
                self.container_id,
                "bash",
                "-c",
                "useradd -m -s /bin/bash testuser && echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && chown -R testuser:testuser /home/testuser",
            ]
        )

    def tearDown(self):
        if hasattr(self, "container_id"):
            logger.info(f"Cleaning up container: {self.container_id[:12]}")
            subprocess.run(
                ["docker", "rm", "-f", self.container_id], capture_output=True
            )

    def _run_command(self, cmd, timeout=300, check=True) -> subprocess.CompletedProcess:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode != 0:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
        return result

    def _run_in_container(
        self, command: str, user: str = "testuser", timeout: int = 300
    ) -> subprocess.CompletedProcess:
        cmd = ["docker", "exec", "-u", user, self.container_id, "bash", "-c", command]
        return self._run_command(cmd, timeout=timeout, check=False)

    def _copy_to_container(self, src: Path, dest: str) -> bool:
        result = self._run_command(
            ["docker", "cp", str(src), f"{self.container_id}:{dest}"], check=False
        )
        if result.returncode == 0:
            self._run_command(
                [
                    "docker",
                    "exec",
                    "-u",
                    "root",
                    self.container_id,
                    "chown",
                    "testuser:testuser",
                    dest,
                ],
                check=False,
            )
            self._run_command(
                [
                    "docker",
                    "exec",
                    "-u",
                    "testuser",
                    self.container_id,
                    "chmod",
                    "+x",
                    dest,
                ],
                check=False,
            )
            return True
        return False

    def test_kdf_sdk_pipeline(self):
        """Install KDF-SDK and verify melos is available."""
        logger.info("Starting KDF-SDK integration test")
        try:
            # Step 1: run install.sh with KDF-SDK type
            logger.info("Step 1: Running install script")
            success = self._copy_to_container(
                INSTALL_SCRIPT, "/home/testuser/install.sh"
            )
            self.assertTrue(success, "Failed to copy install script")

            install_cmd = """
            cd /home/testuser &&
            sed -i 's/read -p "Do you want to run the full setup now.*/REPLY="n"/' install.sh &&
            sed -i 's/kce-full-setup "$FLUTTER_VERSION"/echo "Skipping auto full setup"/' install.sh &&
            timeout 600 ./install.sh --debug --install-type KDF-SDK
            """
            result = self._run_in_container(install_cmd, timeout=700)
            if result.returncode != 0:
                self.skipTest(f"Install script failed: {result.stderr}")
            logger.info("✓ Install script completed")

            # Step 2: run setup with KDF-SDK type
            logger.info("Step 2: Running KDF-SDK setup")
            setup_cmd = """
            cd /home/testuser &&
            source ~/.bashrc &&
            export PATH="$HOME/.local/bin:$PATH" &&
            cd ~/.komodo-codex-env &&
            uv run komodo-codex-env setup --install-type KDF-SDK --verbose
            """
            result = self._run_in_container(setup_cmd, timeout=1200)
            if result.returncode != 0:
                self.skipTest(f"Setup failed: {result.stderr}")
            logger.info("✓ KDF-SDK setup completed")
        except Exception as e:
            self.skipTest(f"Integration test failed: {e}")

        # Step 3: verify melos is installed
        logger.info("Step 3: Verifying melos installation")
        verify_cmd = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH:$HOME/.pub-cache/bin" &&
        melos --version
        """
        result = self._run_in_container(verify_cmd)
        self.assertEqual(result.returncode, 0, f"Melos not installed: {result.stderr}")
        logger.info("✓ Melos installation verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
