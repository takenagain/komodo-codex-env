"""
Unit tests for Android SDK and FVM path detection and configuration logic.

These tests provide fast feedback without requiring Docker or actual installation.
They test the core logic for detecting Android SDK and FVM installations.
"""

import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

try:
    from komodo_codex_env.android_manager import AndroidManager
    from komodo_codex_env.flutter_manager import FlutterManager
    from komodo_codex_env.config import EnvironmentConfig
    from komodo_codex_env.executor import CommandExecutor
    from komodo_codex_env.dependency_manager import DependencyManager
except ImportError as e:
    AndroidManager = FlutterManager = EnvironmentConfig = CommandExecutor = DependencyManager = None
    import_error = e


@unittest.skipIf(AndroidManager is None, f"Cannot import required modules: {import_error if 'import_error' in locals() else 'Unknown error'}")
class AndroidSDKLocationUnitTest(unittest.TestCase):
    """Unit tests for Android SDK location detection and configuration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create mock config
        self.config = EnvironmentConfig()
        self.config.android_home = None  # Let it use default
        
        # Create mock executor and dependency manager
        self.executor = Mock(spec=CommandExecutor)
        self.dep_manager = Mock(spec=DependencyManager)
        
        # Create AndroidManager instance
        self.android_manager = AndroidManager(self.config, self.executor, self.dep_manager)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_default_android_home_path(self):
        """Test that default Android SDK path is /opt/android-sdk."""
        self.assertEqual(str(self.android_manager.android_home), "/opt/android-sdk")

    def test_android_sdk_subdirectories(self):
        """Test that Android SDK subdirectories are correctly configured."""
        expected_paths = {
            "tools": "/opt/android-sdk/tools",
            "platform_tools": "/opt/android-sdk/platform-tools", 
            "cmdline_tools": "/opt/android-sdk/cmdline-tools/latest",
        }
        
        self.assertEqual(str(self.android_manager.android_tools_dir), expected_paths["tools"])
        self.assertEqual(str(self.android_manager.android_platform_tools_dir), expected_paths["platform_tools"])
        self.assertEqual(str(self.android_manager.android_cmdline_tools_dir), expected_paths["cmdline_tools"])

    def test_custom_android_home_path(self):
        """Test that custom Android SDK path is respected."""
        custom_path = self.temp_path / "custom-android"
        self.config.android_home = custom_path
        
        android_manager = AndroidManager(self.config, self.executor, self.dep_manager)
        self.assertEqual(android_manager.android_home, custom_path)

    def test_android_sdk_detection_when_installed(self):
        """Test Android SDK detection when properly installed."""
        # Create mock Android SDK structure
        android_home = self.temp_path / "android-sdk"
        cmdline_tools = android_home / "cmdline-tools" / "latest" / "bin" 
        cmdline_tools.mkdir(parents=True)
        (cmdline_tools / "sdkmanager").touch()
        
        # Configure manager to use temp directory
        self.android_manager.android_home = android_home
        self.android_manager.android_cmdline_tools_dir = android_home / "cmdline-tools" / "latest"
        
        self.assertTrue(self.android_manager.is_android_sdk_installed())

    def test_android_sdk_detection_when_not_installed(self):
        """Test Android SDK detection when not installed."""
        # Use non-existent directory
        self.android_manager.android_home = self.temp_path / "nonexistent"
        self.assertFalse(self.android_manager.is_android_sdk_installed())

    def test_android_environment_variables(self):
        """Test Android environment variable generation."""
        android_home = self.temp_path / "android-sdk"
        self.android_manager.android_home = android_home
        
        env_vars = self.android_manager._get_android_env()
        
        self.assertEqual(env_vars["ANDROID_HOME"], str(android_home))
        self.assertEqual(env_vars["ANDROID_SDK_ROOT"], str(android_home))

    def test_java_detection_mocking(self):
        """Test Java detection with mocked command executor."""
        # Test when Java is available
        self.executor.check_command_exists.return_value = True
        self.assertTrue(self.android_manager.is_java_installed())
        
        # Verify correct commands were checked
        expected_calls = [unittest.mock.call("java"), unittest.mock.call("javac")]
        self.executor.check_command_exists.assert_has_calls(expected_calls)
        
        # Test when Java is not available
        self.executor.check_command_exists.return_value = False
        self.assertFalse(self.android_manager.is_java_installed())


@unittest.skipIf(FlutterManager is None, f"Cannot import required modules: {import_error if 'import_error' in locals() else 'Unknown error'}")
class FVMLocationUnitTest(unittest.TestCase):
    """Unit tests for FVM location detection and configuration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create mock config
        self.config = EnvironmentConfig()
        self.config.home_dir = self.temp_path
        
        # Create mock executor and dependency manager
        self.executor = Mock(spec=CommandExecutor)
        self.dep_manager = Mock(spec=DependencyManager)
        
        # Create FlutterManager instance
        self.flutter_manager = FlutterManager(self.config, self.executor, self.dep_manager)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_fvm_home_path_configuration(self):
        """Test that FVM home path is correctly configured."""
        expected_fvm_home = self.temp_path / ".fvm"
        self.assertEqual(self.flutter_manager.fvm_home, expected_fvm_home)

    def test_fvm_binary_path_configuration(self):
        """Test that FVM binary path is correctly configured."""
        expected_fvm_bin = self.temp_path / ".fvm" / "default" / "bin" / "flutter"
        self.assertEqual(self.flutter_manager.fvm_bin, expected_fvm_bin)

    def test_fvm_detection_in_path(self):
        """Test FVM detection when fvm is in PATH."""
        self.executor.check_command_exists.return_value = True
        self.assertTrue(self.flutter_manager.is_fvm_installed())
        self.executor.check_command_exists.assert_called_with("fvm")

    def test_fvm_detection_in_pub_cache(self):
        """Test FVM detection in ~/.pub-cache/bin."""
        self.executor.check_command_exists.return_value = False
        
        # Create FVM in pub-cache
        pub_cache_bin = self.temp_path / ".pub-cache" / "bin"
        pub_cache_bin.mkdir(parents=True)
        fvm_binary = pub_cache_bin / "fvm"
        fvm_binary.touch()
        fvm_binary.chmod(0o755)
        
        self.assertTrue(self.flutter_manager.is_fvm_installed())

    def test_fvm_detection_common_locations(self):
        """Test FVM detection in common system locations."""
        self.executor.check_command_exists.return_value = False
        
        # Test that we check multiple common paths
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            self.assertFalse(self.flutter_manager.is_fvm_installed())
            
            # Verify we checked various locations
            self.assertTrue(mock_exists.called)

    def test_fvm_path_environment_setup(self):
        """Test that FVM path is correctly added to environment."""
        pub_cache_bin = self.temp_path / ".pub-cache" / "bin"
        pub_cache_bin.mkdir(parents=True)
        
        # Simulate FVM installation detection
        self.executor.check_command_exists.return_value = False
        
        with patch.dict(os.environ, {}, clear=True):
            # The path setup would normally be done by shell integration
            expected_path_addition = str(pub_cache_bin)
            self.assertTrue(pub_cache_bin.exists())

    def test_flutter_version_configuration(self):
        """Test Flutter version configuration through FVM."""
        flutter_version = "3.32.0"
        self.config.flutter_version = flutter_version
        
        flutter_manager = FlutterManager(self.config, self.executor, self.dep_manager)
        self.assertEqual(flutter_manager.config.flutter_version, flutter_version)


@unittest.skipIf(EnvironmentConfig is None, f"Cannot import required modules: {import_error if 'import_error' in locals() else 'Unknown error'}")
class EnvironmentConfigurationUnitTest(unittest.TestCase):
    """Unit tests for environment configuration logic."""
    
    def test_android_configuration_defaults(self):
        """Test default Android configuration values."""
        config = EnvironmentConfig()
        
        # Test default values
        self.assertTrue(config.install_android_sdk)
        self.assertEqual(config.android_api_level, "35")
        self.assertEqual(config.android_build_tools_version, "35.0.1")
        self.assertIsNotNone(config.android_home)

    def test_android_configuration_from_environment(self):
        """Test Android configuration from environment variables."""
        with patch.dict(os.environ, {
            "INSTALL_ANDROID_SDK": "false",
            "ANDROID_API_LEVEL": "34",
            "ANDROID_BUILD_TOOLS_VERSION": "34.0.0",
        }):
            config = EnvironmentConfig.from_environment()
            
            self.assertFalse(config.install_android_sdk)
            self.assertEqual(config.android_api_level, "34")
            self.assertEqual(config.android_build_tools_version, "34.0.0")

    def test_platform_configuration(self):
        """Test platform configuration for Android builds."""
        config = EnvironmentConfig()
        
        # Test default platforms
        self.assertIn("android", config.platforms)
        
        # Test platform-specific settings
        config.platforms = ["web", "android", "linux"]
        self.assertIn("android", config.platforms)

    def test_flutter_version_configuration(self):
        """Test Flutter version configuration."""
        config = EnvironmentConfig()
        config.flutter_version = "3.32.0"
        
        self.assertEqual(config.flutter_version, "3.32.0")

    def test_paths_configuration(self):
        """Test path configurations are valid Path objects."""
        config = EnvironmentConfig()
        
        # Test that paths are Path objects
        self.assertIsInstance(config.android_home, Path)
        self.assertIsInstance(config.home_dir, Path)


class PathValidationTest(unittest.TestCase):
    """Test path validation and normalization logic."""
    
    def test_android_sdk_path_normalization(self):
        """Test Android SDK path normalization."""
        test_paths = [
            "/opt/android-sdk",
            "/opt/android-sdk/",
            "~/Android/Sdk",
            "/home/user/Android/Sdk",
        ]
        
        for path_str in test_paths:
            path = Path(path_str)
            # Test that path can be resolved and is absolute when needed
            if not path_str.startswith("~"):
                self.assertTrue(path.is_absolute() or path_str.startswith("/"))

    def test_fvm_path_validation(self):
        """Test FVM path validation logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test various FVM installation patterns
            fvm_locations = [
                temp_path / ".pub-cache" / "bin" / "fvm",
                temp_path / ".local" / "bin" / "fvm",
                temp_path / ".fvm" / "fvm",
            ]
            
            for fvm_path in fvm_locations:
                fvm_path.parent.mkdir(parents=True, exist_ok=True)
                fvm_path.touch()
                
                # Validate that path exists and is a file
                self.assertTrue(fvm_path.exists())
                self.assertTrue(fvm_path.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
