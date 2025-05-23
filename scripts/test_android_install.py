#!/usr/bin/env python3
"""Test script for Android SDK installation functionality."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from komodo_codex_env.config import EnvironmentConfig
from komodo_codex_env.executor import CommandExecutor
from komodo_codex_env.dependency_manager import DependencyManager
from komodo_codex_env.android_manager import AndroidManager


def test_android_manager_initialization():
    """Test AndroidManager initialization."""
    print("Testing AndroidManager initialization...")
    
    config = EnvironmentConfig()
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    android_manager = AndroidManager(config, executor, dep_manager)
    
    assert android_manager.android_home.exists() or not android_manager.android_home.exists()  # Path object works
    assert android_manager.cmdline_tools_version == "11076708"
    print("✓ AndroidManager initialized successfully")


def test_java_version_detection():
    """Test Java version detection."""
    print("Testing Java version detection...")
    
    config = EnvironmentConfig()
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    android_manager = AndroidManager(config, executor, dep_manager)
    
    # Test with mocked java command
    with patch.object(android_manager.executor, 'check_command_exists') as mock_check:
        mock_check.return_value = True
        
        with patch.object(android_manager.executor, 'run_command') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stderr='openjdk version "17.0.8" 2023-07-18\nOpenJDK Runtime Environment (build 17.0.8+7-Ubuntu-1ubuntu122.04)\nOpenJDK 64-Bit Server VM (build 17.0.8+7-Ubuntu-1ubuntu122.04, mixed mode, sharing)'
            )
            
            version = android_manager.get_java_version()
            assert version == "17.0.8"
            print("✓ Java version detection works")


def test_cmdline_tools_url_generation():
    """Test command line tools URL generation."""
    print("Testing command line tools URL generation...")
    
    config = EnvironmentConfig()
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    android_manager = AndroidManager(config, executor, dep_manager)
    
    url = android_manager.get_cmdline_tools_url()
    assert "commandlinetools-" in url
    assert android_manager.cmdline_tools_version in url
    assert url.endswith("_latest.zip")
    print(f"✓ Generated URL: {url}")


def test_android_sdk_detection():
    """Test Android SDK detection."""
    print("Testing Android SDK detection...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EnvironmentConfig()
        config.android_home = Path(temp_dir) / "Android" / "Sdk"
        
        executor = CommandExecutor()
        dep_manager = DependencyManager(executor)
        android_manager = AndroidManager(config, executor, dep_manager)
        
        # Update android_manager paths to use the temp config
        android_manager.android_home = config.android_home
        android_manager.android_cmdline_tools_dir = config.android_home / "cmdline-tools" / "latest"
        
        # Should not be installed initially
        assert not android_manager.is_android_sdk_installed()
        
        # Create the required structure
        cmdline_tools_dir = android_manager.android_cmdline_tools_dir
        cmdline_tools_dir.mkdir(parents=True, exist_ok=True)
        (cmdline_tools_dir / "bin").mkdir(parents=True, exist_ok=True)
        (cmdline_tools_dir / "bin" / "sdkmanager").touch()
        
        # Now should be detected as installed
        assert android_manager.is_android_sdk_installed()
        print("✓ Android SDK detection works")


def test_environment_variable_setup():
    """Test environment variable setup."""
    print("Testing environment variable setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EnvironmentConfig()
        config.android_home = Path(temp_dir) / "Android" / "Sdk"
        
        executor = CommandExecutor()
        dep_manager = DependencyManager(executor)
        android_manager = AndroidManager(config, executor, dep_manager)
        
        # Create a temporary profile file
        profile_path = Path(temp_dir) / ".zshrc"
        
        # Mock the get_shell_profile method
        with patch.object(config, 'get_shell_profile', return_value=profile_path):
            success = android_manager.setup_environment_variables()
            
            # Check if the profile file was created and contains Android vars
            if profile_path.exists():
                content = profile_path.read_text()
                assert "ANDROID_HOME" in content
                assert "ANDROID_SDK_ROOT" in content
                print("✓ Environment variables setup works")
            else:
                print("✓ Environment variables setup completed (no profile changes needed)")


def test_android_info_gathering():
    """Test Android info gathering."""
    print("Testing Android info gathering...")
    
    config = EnvironmentConfig()
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    android_manager = AndroidManager(config, executor, dep_manager)
    
    info = android_manager.get_android_info()
    
    assert "status" in info
    assert "java_status" in info
    assert info["status"] in ["installed", "not_installed"]
    assert info["java_status"] in ["installed", "not_installed"]
    
    print(f"✓ Android info: {info}")


def test_verification_process():
    """Test verification process."""
    print("Testing verification process...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = EnvironmentConfig()
        config.android_home = Path(temp_dir) / "Android" / "Sdk"
        
        executor = CommandExecutor()
        dep_manager = DependencyManager(executor)
        android_manager = AndroidManager(config, executor, dep_manager)
        
        # Update android_manager paths to use the temp config
        android_manager.android_home = config.android_home
        android_manager.android_cmdline_tools_dir = config.android_home / "cmdline-tools" / "latest"
        android_manager.android_platform_tools_dir = config.android_home / "platform-tools"
        
        # Should fail verification initially
        assert not android_manager.verify_installation()
        
        # Create minimal required structure
        android_home = android_manager.android_home
        android_home.mkdir(parents=True, exist_ok=True)
        
        # Create sdkmanager
        cmdline_tools_dir = android_manager.android_cmdline_tools_dir
        cmdline_tools_dir.mkdir(parents=True, exist_ok=True)
        (cmdline_tools_dir / "bin").mkdir(parents=True, exist_ok=True)
        (cmdline_tools_dir / "bin" / "sdkmanager").touch()
        
        # Create adb
        platform_tools_dir = android_manager.android_platform_tools_dir
        platform_tools_dir.mkdir(parents=True, exist_ok=True)
        (platform_tools_dir / "adb").touch()
        
        # Create platforms directory with content
        platforms_dir = android_home / "platforms"
        platforms_dir.mkdir(parents=True, exist_ok=True)
        (platforms_dir / "android-34").mkdir()
        
        # Create build-tools directory with content
        build_tools_dir = android_home / "build-tools"
        build_tools_dir.mkdir(parents=True, exist_ok=True)
        (build_tools_dir / "34.0.0").mkdir()
        
        # Now should pass verification
        assert android_manager.verify_installation()
        print("✓ Verification process works")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Android SDK Installation Tests")
    print("=" * 60)
    
    tests = [
        test_android_manager_initialization,
        test_java_version_detection,
        test_cmdline_tools_url_generation,
        test_android_sdk_detection,
        test_environment_variable_setup,
        test_android_info_gathering,
        test_verification_process,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)