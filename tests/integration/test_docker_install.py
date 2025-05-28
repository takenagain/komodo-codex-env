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
        
        # Create testuser if it doesn't exist
        create_user_cmd = [
            "docker", "exec", "-u", "root", self.container_id, "bash", "-c",
            "id testuser || (useradd -m -s /bin/bash testuser && echo 'testuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers)"
        ]
        result = subprocess.run(create_user_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to create testuser: {result.stderr}")

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
        
        # Debug: Check user exists
        check_user_cmd = ["docker", "exec", self.container_id, "id", user]
        check_result = subprocess.run(check_user_cmd, capture_output=True, text=True)
        if check_result.returncode != 0:
            print(f"User {user} not found: {check_result.stdout}{check_result.stderr}")
        
        # Debug: List users
        list_users_cmd = ["docker", "exec", self.container_id, "bash", "-c", "cat /etc/passwd | grep -E '/home|/root'"]
        list_result = subprocess.run(list_users_cmd, capture_output=True, text=True)
        print(f"Available users: {list_result.stdout}")
        
        # Make sure the script is executable
        chmod_cmd = ["docker", "exec", self.container_id, "chmod", "+x", "/tmp/install.sh"]
        subprocess.run(chmod_cmd, capture_output=True)
        
        # Run basic install script only (it automatically runs full setup by default)
        # We'll extend timeout to handle the full installation
        cmd = [
            "docker",
            "exec",
            "-u",
            user,
            self.container_id,
            "bash",
            "-c",
            f"cd {home_dir} && timeout 1500 bash /tmp/install.sh --debug {extra_args} || true",
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    def verify_installation(self, user="testuser") -> bool:
        home_dir = "/home/testuser" if user == "testuser" else "/root"
        
        # First check if the basic installation directory exists
        check_dir_cmd = [
            "docker", "exec", "-u", user, self.container_id,
            "test", "-d", f"{home_dir}/.komodo-codex-env"
        ]
        dir_result = subprocess.run(check_dir_cmd, capture_output=True, text=True)
        if dir_result.returncode != 0:
            print(f"Installation directory not found at {home_dir}/.komodo-codex-env")
            return False
        
        # Try UV entry point first (more reliable)
        uv_cmd = [
            "docker", "exec", "-u", user, self.container_id, "bash", "-c",
            f"cd {home_dir}/.komodo-codex-env && export PATH=\"$HOME/.local/bin:$PATH\" && uv run komodo-codex-env --version"
        ]
        uv_result = subprocess.run(uv_cmd, capture_output=True, text=True)
        if uv_result.returncode == 0:
            return True
        
        # Fallback to venv activation
        venv_cmd = [
            "docker", "exec", "-u", user, self.container_id, "bash", "-c",
            f"cd {home_dir}/.komodo-codex-env && source .venv/bin/activate && python -m komodo_codex_env.cli --version"
        ]
        venv_result = subprocess.run(venv_cmd, capture_output=True, text=True)
        return venv_result.returncode == 0

    def test_basic_install_non_root(self):
        self.copy_install_script()
        result = self.run_install(user="testuser")
        
        # The install script might time out during the lengthy Android SDK installation
        # but still have completed the basic installation successfully
        print(f"Install script exit code: {result.returncode}")
        print(f"Last part of stdout: {result.stdout[-1000:] if result.stdout else 'No stdout'}")
        
        # Check if basic installation was successful regardless of exit code
        installation_verified = self.verify_installation(user="testuser")
        
        if not installation_verified and result.returncode != 0:
            self.fail(f"Install script failed with exit code {result.returncode} and installation verification failed.\nSTDOUT: {result.stdout[-2000:]}\nSTDERR: {result.stderr}")
        
        self.assertTrue(installation_verified, "Installation verification failed - komodo-codex-env not properly installed")

    def test_root_install(self):
        self.copy_install_script()
        result = self.run_install(user="root", extra_args="--allow-root")
        if result.returncode != 0:
            self.fail(f"Install script failed with exit code {result.returncode}.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        self.assertTrue(self.verify_installation(user="root"))

    def test_uv_entry_point_availability(self):
        self.copy_install_script()
        install_result = self.run_install(user="testuser")
        
        # Similar to basic install test, handle timeout gracefully
        print(f"Install script exit code: {install_result.returncode}")
        
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
        
        if result.returncode != 0:
            print(f"UV entry point failed. STDOUT: {result.stdout}, STDERR: {result.stderr}")
            # Also check if basic installation directory exists for debugging
            check_cmd = ["docker", "exec", "-u", "testuser", self.container_id, "ls", "-la", "/home/testuser/.komodo-codex-env/"]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            print(f"Installation directory contents: {check_result.stdout}")
        
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
