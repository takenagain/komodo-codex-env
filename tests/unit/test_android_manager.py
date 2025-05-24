import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

try:
    import rich, requests
    from komodo_codex_env.config import EnvironmentConfig
    from komodo_codex_env.executor import CommandExecutor
    from komodo_codex_env.dependency_manager import DependencyManager
    from komodo_codex_env.android_manager import AndroidManager
except ImportError:
    rich = None
    requests = None
    EnvironmentConfig = CommandExecutor = DependencyManager = AndroidManager = None


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class AndroidManagerTests(unittest.TestCase):
    def setUp(self):
        self.config = EnvironmentConfig()
        self.executor = CommandExecutor()
        self.dep_manager = DependencyManager(self.executor)
        self.android_manager = AndroidManager(self.config, self.executor, self.dep_manager)

    def test_android_manager_initialization(self):
        self.assertEqual(self.android_manager.cmdline_tools_version, "11076708")

    def test_java_version_detection(self):
        with patch.object(self.android_manager.executor, "check_command_exists", return_value=True):
            with patch.object(self.android_manager.executor, "run_command") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stderr='openjdk version "17.0.8" 2023-07-18\nOpenJDK Runtime Environment (build 17.0.8+7-Ubuntu-1ubuntu122.04)\nOpenJDK 64-Bit Server VM (build 17.0.8+7-Ubuntu-1ubuntu122.04, mixed mode, sharing)'
                )
                version = self.android_manager.get_java_version()
                self.assertEqual(version, "17.0.8")

    def test_cmdline_tools_url_generation(self):
        url = self.android_manager.get_cmdline_tools_url()
        self.assertIn("commandlinetools-", url)
        self.assertIn(self.android_manager.cmdline_tools_version, url)
        self.assertTrue(url.endswith("_latest.zip"))

    def test_android_sdk_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.android_home = Path(temp_dir) / "Android" / "Sdk"
            manager = AndroidManager(self.config, self.executor, self.dep_manager)
            manager.android_home = self.config.android_home
            manager.android_cmdline_tools_dir = self.config.android_home / "cmdline-tools" / "latest"

            self.assertFalse(manager.is_android_sdk_installed())

            cmdline_tools_dir = manager.android_cmdline_tools_dir
            cmdline_tools_dir.mkdir(parents=True, exist_ok=True)
            (cmdline_tools_dir / "bin").mkdir(parents=True, exist_ok=True)
            (cmdline_tools_dir / "bin" / "sdkmanager").touch()

            self.assertTrue(manager.is_android_sdk_installed())

    def test_environment_variable_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.android_home = Path(temp_dir) / "Android" / "Sdk"
            manager = AndroidManager(self.config, self.executor, self.dep_manager)
            profile_path = Path(temp_dir) / ".zshrc"
            with patch.object(self.config, "get_shell_profile", return_value=profile_path):
                success = manager.setup_environment_variables()
                self.assertTrue(success)
                if profile_path.exists():
                    content = profile_path.read_text()
                    self.assertIn("ANDROID_HOME", content)
                    self.assertIn("ANDROID_SDK_ROOT", content)

    def test_android_info_gathering(self):
        info = self.android_manager.get_android_info()
        self.assertIn("status", info)
        self.assertIn("java_status", info)
        self.assertIn(info["status"], ["installed", "not_installed"])
        self.assertIn(info["java_status"], ["installed", "not_installed"])

    def test_verification_process(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.config.android_home = Path(temp_dir) / "Android" / "Sdk"
            manager = AndroidManager(self.config, self.executor, self.dep_manager)
            manager.android_home = self.config.android_home
            manager.android_cmdline_tools_dir = self.config.android_home / "cmdline-tools" / "latest"
            manager.android_platform_tools_dir = self.config.android_home / "platform-tools"

            self.assertFalse(manager.verify_installation())

            android_home = manager.android_home
            android_home.mkdir(parents=True, exist_ok=True)

            cmdline_tools_dir = manager.android_cmdline_tools_dir
            cmdline_tools_dir.mkdir(parents=True, exist_ok=True)
            (cmdline_tools_dir / "bin").mkdir(parents=True, exist_ok=True)
            (cmdline_tools_dir / "bin" / "sdkmanager").touch()

            platform_tools_dir = manager.android_platform_tools_dir
            platform_tools_dir.mkdir(parents=True, exist_ok=True)
            (platform_tools_dir / "adb").touch()

            platforms_dir = android_home / "platforms"
            platforms_dir.mkdir(parents=True, exist_ok=True)
            (platforms_dir / "android-34").mkdir()

            build_tools_dir = android_home / "build-tools"
            build_tools_dir.mkdir(parents=True, exist_ok=True)
            (build_tools_dir / "34.0.0").mkdir()

            self.assertTrue(manager.verify_installation())


if __name__ == "__main__":
    unittest.main()
