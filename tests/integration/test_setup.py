import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
try:
    import rich, requests
    from komodo_codex_env.config import EnvironmentConfig
    from komodo_codex_env.setup import EnvironmentSetup
except ImportError:
    rich = None
    requests = None
    EnvironmentConfig = EnvironmentSetup = None


@unittest.skipUnless(rich and requests, "Required dependencies not installed")
class SetupIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_flutter_android_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "android"]
            config.install_android_sdk = True
            config.parallel_execution = True
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)
            config.android_home = Path(temp_dir) / "Android" / "Sdk"

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=True)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=True)
            setup.android_manager.get_android_info = Mock(return_value={
                "status": "installed",
                "java_status": "installed",
                "android_home": str(config.android_home),
            })

            success = await setup._setup_flutter_and_android()
            self.assertTrue(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_called_once()
            setup.android_manager.install_android_sdk.assert_called_once()

    async def test_sequential_flutter_android_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "android"]
            config.install_android_sdk = True
            config.parallel_execution = False
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)
            config.android_home = Path(temp_dir) / "Android" / "Sdk"

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=True)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=True)

            success = await setup._setup_flutter_and_android()
            self.assertTrue(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_called_once()
            setup.android_manager.install_android_sdk.assert_called_once()

    async def test_android_skip_when_not_in_platforms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "linux"]
            config.install_android_sdk = True
            config.parallel_execution = True
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=True)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=True)

            success = await setup._setup_flutter_and_android()
            self.assertTrue(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_called_once()
            setup.android_manager.install_android_sdk.assert_not_called()

    async def test_android_skip_when_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "android"]
            config.install_android_sdk = False
            config.parallel_execution = True
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=True)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=True)

            success = await setup._setup_flutter_and_android()
            self.assertTrue(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_called_once()
            setup.android_manager.install_android_sdk.assert_not_called()

    async def test_flutter_failure_stops_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "android"]
            config.install_android_sdk = True
            config.parallel_execution = True
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=False)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=True)

            success = await setup._setup_flutter_and_android()
            self.assertFalse(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_not_called()

    async def test_android_failure_does_not_stop_setup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = EnvironmentConfig()
            config.platforms = ["web", "android"]
            config.install_android_sdk = True
            config.parallel_execution = True
            config.flutter_version = "3.32.0"
            config.initial_dir = Path(temp_dir)

            setup = EnvironmentSetup(config)
            setup.flutter_manager.install_flutter = Mock(return_value=True)
            setup.flutter_manager.configure_flutter = Mock(return_value=True)
            setup.android_manager.install_android_sdk = Mock(return_value=False)

            success = await setup._setup_flutter_and_android()
            self.assertTrue(success)
            setup.flutter_manager.install_flutter.assert_called_once()
            setup.flutter_manager.configure_flutter.assert_called_once()
            setup.android_manager.install_android_sdk.assert_called_once()

    def test_config_android_settings(self):
        config = EnvironmentConfig()
        self.assertTrue(config.install_android_sdk)
        self.assertEqual(config.android_api_level, "35")
        self.assertEqual(config.android_build_tools_version, "35.0.1")
        self.assertIsNotNone(config.android_home)

        with patch.dict(os.environ, {"INSTALL_ANDROID_SDK": "false"}):
            config = EnvironmentConfig.from_environment()
            self.assertFalse(config.install_android_sdk)


if __name__ == "__main__":
    unittest.main()
