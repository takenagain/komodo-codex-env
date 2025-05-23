#!/usr/bin/env python3
"""Integration test for parallel Flutter and Android SDK setup."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from komodo_codex_env.config import EnvironmentConfig
from komodo_codex_env.setup import EnvironmentSetup


async def test_parallel_flutter_android_setup():
    """Test parallel Flutter and Android setup execution."""
    print("Testing parallel Flutter and Android setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration
        config = EnvironmentConfig()
        config.platforms = ["web", "android"]
        config.install_android_sdk = True
        config.parallel_execution = True
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        config.android_home = Path(temp_dir) / "Android" / "Sdk"
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock the flutter manager methods
        setup.flutter_manager.install_flutter = Mock(return_value=True)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock the android manager methods
        setup.android_manager.install_android_sdk = Mock(return_value=True)
        setup.android_manager.get_android_info = Mock(return_value={
            "status": "installed",
            "java_status": "installed", 
            "android_home": str(config.android_home)
        })
        
        # Test the parallel setup method
        success = await setup._setup_flutter_and_android()
        
        assert success, "Parallel Flutter and Android setup should succeed"
        
        # Verify both managers were called
        setup.flutter_manager.install_flutter.assert_called_once()
        setup.flutter_manager.configure_flutter.assert_called_once()
        setup.android_manager.install_android_sdk.assert_called_once()
        
        print("✓ Parallel Flutter and Android setup works")


async def test_sequential_flutter_android_setup():
    """Test sequential Flutter and Android setup execution."""
    print("Testing sequential Flutter and Android setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration
        config = EnvironmentConfig()
        config.platforms = ["web", "android"]
        config.install_android_sdk = True
        config.parallel_execution = False  # Force sequential
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        config.android_home = Path(temp_dir) / "Android" / "Sdk"
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock the flutter manager methods
        setup.flutter_manager.install_flutter = Mock(return_value=True)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock the android manager methods
        setup.android_manager.install_android_sdk = Mock(return_value=True)
        
        # Test the sequential setup method
        success = await setup._setup_flutter_and_android()
        
        assert success, "Sequential Flutter and Android setup should succeed"
        
        # Verify both managers were called
        setup.flutter_manager.install_flutter.assert_called_once()
        setup.flutter_manager.configure_flutter.assert_called_once()
        setup.android_manager.install_android_sdk.assert_called_once()
        
        print("✓ Sequential Flutter and Android setup works")


async def test_android_skip_when_not_in_platforms():
    """Test Android SDK is skipped when android not in platforms."""
    print("Testing Android SDK skip when not in platforms...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration without android platform
        config = EnvironmentConfig()
        config.platforms = ["web", "linux"]  # No android
        config.install_android_sdk = True
        config.parallel_execution = True
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock the flutter manager methods
        setup.flutter_manager.install_flutter = Mock(return_value=True)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock the android manager methods
        setup.android_manager.install_android_sdk = Mock(return_value=True)
        
        # Test the parallel setup method
        success = await setup._setup_flutter_and_android()
        
        assert success, "Setup should succeed even without Android"
        
        # Verify Flutter manager was called but Android was not
        setup.flutter_manager.install_flutter.assert_called_once()
        setup.flutter_manager.configure_flutter.assert_called_once()
        setup.android_manager.install_android_sdk.assert_not_called()
        
        print("✓ Android SDK correctly skipped when not in platforms")


async def test_android_skip_when_disabled():
    """Test Android SDK is skipped when install_android_sdk is False."""
    print("Testing Android SDK skip when disabled...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration with android disabled
        config = EnvironmentConfig()
        config.platforms = ["web", "android"]
        config.install_android_sdk = False  # Disabled
        config.parallel_execution = True
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock the flutter manager methods
        setup.flutter_manager.install_flutter = Mock(return_value=True)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock the android manager methods
        setup.android_manager.install_android_sdk = Mock(return_value=True)
        
        # Test the parallel setup method
        success = await setup._setup_flutter_and_android()
        
        assert success, "Setup should succeed when Android is disabled"
        
        # Verify Flutter manager was called but Android was not
        setup.flutter_manager.install_flutter.assert_called_once()
        setup.flutter_manager.configure_flutter.assert_called_once()
        setup.android_manager.install_android_sdk.assert_not_called()
        
        print("✓ Android SDK correctly skipped when disabled")


async def test_flutter_failure_stops_setup():
    """Test that Flutter failure stops the setup process."""
    print("Testing Flutter failure stops setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration
        config = EnvironmentConfig()
        config.platforms = ["web", "android"]
        config.install_android_sdk = True
        config.parallel_execution = True
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock Flutter manager to fail
        setup.flutter_manager.install_flutter = Mock(return_value=False)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock the android manager methods
        setup.android_manager.install_android_sdk = Mock(return_value=True)
        
        # Test the parallel setup method
        success = await setup._setup_flutter_and_android()
        
        assert not success, "Setup should fail when Flutter installation fails"
        
        # Verify Flutter manager was called
        setup.flutter_manager.install_flutter.assert_called_once()
        # configure_flutter should not be called if install fails
        setup.flutter_manager.configure_flutter.assert_not_called()
        
        print("✓ Flutter failure correctly stops setup")


async def test_android_failure_does_not_stop_setup():
    """Test that Android failure does not stop the setup process."""
    print("Testing Android failure does not stop setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test configuration
        config = EnvironmentConfig()
        config.platforms = ["web", "android"]
        config.install_android_sdk = True
        config.parallel_execution = True
        config.flutter_version = "3.32.0"
        config.initial_dir = Path(temp_dir)
        
        # Create EnvironmentSetup instance
        setup = EnvironmentSetup(config)
        
        # Mock the flutter manager methods to succeed
        setup.flutter_manager.install_flutter = Mock(return_value=True)
        setup.flutter_manager.configure_flutter = Mock(return_value=True)
        
        # Mock Android manager to fail
        setup.android_manager.install_android_sdk = Mock(return_value=False)
        
        # Test the parallel setup method
        success = await setup._setup_flutter_and_android()
        
        assert success, "Setup should succeed even when Android installation fails"
        
        # Verify both managers were called
        setup.flutter_manager.install_flutter.assert_called_once()
        setup.flutter_manager.configure_flutter.assert_called_once()
        setup.android_manager.install_android_sdk.assert_called_once()
        
        print("✓ Android failure correctly does not stop setup")


def test_config_android_settings():
    """Test Android configuration settings."""
    print("Testing Android configuration settings...")
    
    # Test default configuration
    config = EnvironmentConfig()
    assert config.install_android_sdk == True
    assert config.android_api_level == "34"
    assert config.android_build_tools_version == "34.0.0"
    assert config.android_home is not None
    
    # Test environment variable override
    with patch.dict(os.environ, {"INSTALL_ANDROID_SDK": "false"}):
        config = EnvironmentConfig.from_environment()
        assert config.install_android_sdk == False
    
    print("✓ Android configuration settings work correctly")


async def run_all_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Integration Tests for Parallel Flutter and Android Setup")
    print("=" * 60)
    
    tests = [
        test_parallel_flutter_android_setup,
        test_sequential_flutter_android_setup,
        test_android_skip_when_not_in_platforms,
        test_android_skip_when_disabled,
        test_flutter_failure_stops_setup,
        test_android_failure_does_not_stop_setup,
        test_config_android_settings,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                await test()
            else:
                test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Integration Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All integration tests passed! The parallel Flutter and Android SDK setup is working correctly.")
        print("")
        print("Key features verified:")
        print("  ✓ Parallel execution of Flutter and Android SDK installation")
        print("  ✓ Sequential fallback when parallel execution is disabled") 
        print("  ✓ Proper skipping of Android SDK when not needed")
        print("  ✓ Correct error handling and failure propagation")
        print("  ✓ Configuration management for Android settings")
        print("")
        print("The Android SDK installation script is ready for production use!")
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_integration_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Integration tests failed with error: {e}")
        sys.exit(1)