# Android SDK Installation and Usage Guide

This guide covers the Android SDK installation features included in the Komodo Codex Environment Setup Tool, specifically designed for building Android APKs with Flutter.

## Overview

The Android SDK installation is integrated as a parallel setup step alongside the Flutter manager, providing:

- Automatic Java Development Kit (JDK) installation
- Android SDK Command Line Tools download and setup
- Essential Android packages installation
- Environment variable configuration
- Cross-platform support (Linux, macOS, Windows)

## Quick Start

### Option 1: Full Environment Setup with Android

```bash
# Install Flutter + Android SDK in parallel
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android

# Or with verbose output
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android --verbose
```

### Option 2: Android SDK Only

```bash
# Using the CLI
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-install
```

### Option 3: Skip Android SDK

```bash
# Skip Android SDK installation
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --no-android
```

## Installation Components

### What Gets Installed

1. **Java Development Kit (OpenJDK 17)**
   - Linux: `openjdk-17-jdk` via apt/yum/pacman
   - macOS: `openjdk@17` via Homebrew
   - Windows: Manual installation guidance

2. **Android SDK Command Line Tools**
   - Latest version (13114758) downloaded from Google
   - Extracted to `~/Android/Sdk/cmdline-tools/latest/`

3. **Essential Android Packages**
   - `platform-tools` (adb, fastboot)
   - `platforms;android-35` (Latest stable API)
   - `platforms;android-34` (Previous stable API)
   - `platforms;android-33` (Earlier stable API)
   - `build-tools;35.0.1`
   - `build-tools;34.0.0`
   - `emulator`
   - `system-images;android-35;google_apis;x86_64`

4. **Environment Variables**
   - `ANDROID_HOME`: Points to Android SDK directory
   - `ANDROID_SDK_ROOT`: Same as ANDROID_HOME
   - PATH additions for command line tools

## Directory Structure

After installation, your Android SDK will be organized as:

```
~/Android/Sdk/
├── cmdline-tools/
│   └── latest/
│       ├── bin/
│       │   ├── sdkmanager
│       │   └── avdmanager
│       └── lib/
├── platform-tools/
│   ├── adb
│   └── fastboot
├── platforms/
│   ├── android-33/
│   ├── android-34/
│   └── android-35/
├── build-tools/
│   ├── 33.0.1/
│   ├── 34.0.0/
│   └── 35.0.1/
├── emulator/
└── system-images/
    └── android-35/
        └── google_apis/
            └── x86_64/
```

## Command Reference

### Status and Information

```bash
# Check Android SDK installation status
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-status

# Check overall Flutter environment
PYTHONPATH=src rye run python -m komodo_codex_env.cli flutter-status
```

### Installation Commands

```bash
# Install Android SDK
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-install

# Accept Android licenses
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-licenses
```

### CLI Command Options

```bash
# Using the main CLI tool
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-install

# Check Android SDK status
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-status

# Accept Android licenses
PYTHONPATH=src rye run python -m komodo_codex_env.cli android-licenses
```

## Environment Variables

### Configuration Options

```bash
# Skip Android SDK installation entirely
export INSTALL_ANDROID_SDK=false

# Custom Android SDK directory
export ANDROID_HOME=/custom/path/to/android/sdk

# Skip Java installation
export SKIP_JAVA_INSTALL=true
```

### Runtime Environment

After installation, these variables are automatically configured:

```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"
export PATH="$PATH:$ANDROID_HOME/platform-tools"
export PATH="$PATH:$ANDROID_HOME/tools/bin"
```

## Flutter Android Development Workflow

### 1. Verify Installation

```bash
# Check Flutter can see Android tools
flutter doctor

# Accept any remaining licenses
flutter doctor --android-licenses
```

### 2. Device Setup

```bash
# List available devices and emulators
flutter devices

# List available emulators
flutter emulators

# Launch an emulator
flutter emulators --launch <emulator_id>
```

### 3. Build APKs

```bash
# Debug APK
flutter build apk --debug

# Release APK
flutter build apk --release

# App Bundle for Play Store
flutter build appbundle --release
```

### 4. Install and Run

```bash
# Install on connected device
flutter install

# Run on device
flutter run

# Run on specific device
flutter run -d <device_id>
```

## Parallel Execution Benefits

When using the main setup command with `android` in platforms, the tool runs Flutter and Android SDK installation in parallel:

```bash
# This runs Flutter FVM setup and Android SDK installation simultaneously
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android
```

**Benefits:**
- Faster overall setup time
- Independent failure handling (Flutter failure stops setup, Android failure continues)
- Better resource utilization during downloads
- Async execution with proper dependency management

## Platform-Specific Notes

### Linux (Ubuntu/Debian)

```bash
# Additional packages installed automatically
sudo apt update
sudo apt install -y openjdk-17-jdk curl unzip
```

### macOS

```bash
# Requires Homebrew
brew install openjdk@17
```

### Windows

Manual Java installation required. Download from:
- https://adoptium.net/temurin/releases/

## Troubleshooting

### Common Issues

1. **Java not found after installation**
   ```bash
   # Restart terminal or source profile
   source ~/.zshrc  # or ~/.bashrc
   ```

2. **Android licenses not accepted**
   ```bash
   # Run license acceptance
   flutter doctor --android-licenses
   ```

3. **Permission denied errors**
   ```bash
   # Ensure user has write access to home directory
   ls -la ~/Android/
   ```

4. **Network/download issues**
   ```bash
   # Check internet connectivity
   curl -I https://dl.google.com/android/repository/

   # Verify sufficient disk space (5GB+ required)
   df -h ~
   ```

### Debug Mode

```bash
# Run with verbose output for debugging
PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms android --verbose

# Check detailed Flutter doctor output
flutter doctor -v
```

### Manual Verification

```bash
# Check if Android SDK tools are in PATH
which adb
which sdkmanager

# List installed Android packages
sdkmanager --list

# Check Android platforms
ls ~/Android/Sdk/platforms/
```

## Integration Examples

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Setup Flutter with Android SDK
  run: |
    PYTHONPATH=src rye run python -m komodo_codex_env.cli setup --platforms web,android --no-docs
    
- name: Build APK
  run: |
    flutter build apk --release
```

### Docker Container

```dockerfile
# Dockerfile example
RUN PYTHONPATH=src python -m komodo_codex_env.cli setup --platforms android --no-docs
```

### Custom Scripts

```bash
#!/bin/bash
# Custom setup script

# Install with custom configuration
export ANDROID_HOME="/opt/android-sdk"
export PLATFORMS="web,android,linux"

PYTHONPATH=src rye run python -m komodo_codex_env.cli setup \
  --platforms $PLATFORMS \
  --flutter-version 3.32.0 \
  --verbose
```

## Advanced Usage

### Multiple Android API Levels

```bash
# Install additional API levels after setup
sdkmanager "platforms;android-32"
sdkmanager "platforms;android-31"
```

### Custom Build Tools

```bash
# Install specific build tools version
sdkmanager "build-tools;33.0.2"
```

### Emulator Management

```bash
# Create new AVD
avdmanager create avd -n test_device -k "system-images;android-35;google_apis;x86_64"

# List AVDs
avdmanager list avd

# Delete AVD
avdmanager delete avd -n test_device
```

## Support and Maintenance

The Android SDK installation is maintained as part of the Komodo Codex Environment Setup Tool. For issues:

1. Check the troubleshooting section above
2. Run with `--verbose` flag for detailed output
3. Verify system requirements and permissions
4. Check Flutter doctor output

The installation automatically handles updates when you re-run the setup command.