import subprocess
import time
import unittest
from pathlib import Path

try:
    import rich, requests
except ImportError:
    rich = None
    requests = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class DockerInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not docker_available():
            raise unittest.SkipTest("Docker is not available")
        result = subprocess.run(
            ["docker", "build", "-t", "komodo-codex-env-test", "-f", str(DOCKERFILE), str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Docker image: {result.stderr}")
        cls.image_name = "komodo-codex-env-test"

    def setUp(self):
        result = subprocess.run(
            ["docker", "run", "-d", "--name", f"komodo-test-{int(time.time())}", self.image_name, "sleep", "3600"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.skipTest("Failed to start Docker container")
        self.container_id = result.stdout.strip()

    def tearDown(self):
        if hasattr(self, "container_id"):
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)

    def copy_install_script(self):
        result = subprocess.run(
            ["docker", "cp", str(INSTALL_SCRIPT), f"{self.container_id}:/tmp/install.sh"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.fail(f"Failed to copy install script: {result.stderr}")

    def run_install(self, user="testuser", extra_args=""):
        home_dir = "/home/testuser" if user == "testuser" else "/root"
        cmd = [
            "docker",
            "exec",
            "-u",
            user,
            self.container_id,
            "bash",
            "-c",
            f"cd {home_dir} && bash /tmp/install.sh --debug {extra_args}",
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    def verify_installation(self, user="testuser") -> bool:
        home_dir = "/home/testuser" if user == "testuser" else "/root"
        cmd = [
            "docker",
            "exec",
            "-u",
            user,
            self.container_id,
            "bash",
            "-c",
            f"cd {home_dir}/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def test_basic_install_non_root(self):
        self.copy_install_script()
        result = self.run_install(user="testuser")
        if result.returncode != 0:
            self.fail(f"Install script failed: {result.stderr}")
        self.assertTrue(self.verify_installation(user="testuser"))

    def test_root_install(self):
        self.copy_install_script()
        result = self.run_install(user="root", extra_args="--allow-root")
        if result.returncode != 0:
            self.fail(f"Install script failed: {result.stderr}")
        self.assertTrue(self.verify_installation(user="root"))

    def test_uv_entry_point_availability(self):
        self.copy_install_script()
        result = self.run_install(user="testuser")
        if result.returncode != 0:
            self.fail("Install script failed")
        cmd = [
            "docker",
            "exec",
            "-u",
            "testuser",
            self.container_id,
            "bash",
            "-c",
            'cd /home/testuser/.komodo-codex-env && export PATH="$HOME/.local/bin:$PATH" && uv run komodo-codex-env --version',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
