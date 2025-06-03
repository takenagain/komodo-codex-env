import unittest
from unittest.mock import patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from komodo_codex_env.config import EnvironmentConfig
from komodo_codex_env.setup import EnvironmentSetup
from komodo_codex_env.flutter_manager import FlutterManager


class SystemDependencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_node_dependencies_added_for_web(self):
        config = EnvironmentConfig()
        config.platforms = ["web"]
        setup = EnvironmentSetup(config)

        with patch.object(setup.dep_manager, "install_dependencies", return_value=True) as mock_install:
            await setup._setup_system_dependencies()
            deps = mock_install.call_args.args[0]
            self.assertIn("nodejs", deps)
            self.assertIn("npm", deps)

    async def test_flutter_install_fails_without_disk_space(self):
        config = EnvironmentConfig()
        env_setup = EnvironmentSetup(config)
        flutter_mgr = FlutterManager(config, env_setup.executor, env_setup.dep_manager)

        with patch.object(flutter_mgr, "install_fvm", return_value=True), \
             patch.object(flutter_mgr.dep_manager, "check_disk_space", return_value=False):
            success = flutter_mgr.install_flutter()
            self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()

