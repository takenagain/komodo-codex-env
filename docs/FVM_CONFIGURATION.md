# FVM Configuration Fix

This document describes the fix implemented to ensure FVM (Flutter Version Management) is properly configured for both the `komodo` user and the `root` user in the Komodo Codex Environment.

## Problem

Previously, FVM was not being found in the environment because:

1. FVM installation only happened during Python setup, not during the initial install script
2. FVM was only configured for the current user running the setup
3. PATH configuration was not applied to multiple users (komodo user and root user)
4. The system didn't check for FVM in common installation locations

## Solution

### 1. Install Script Changes (`install.sh`)

**Added FVM Installation Step:**

- New `install_fvm()` function that installs FVM for multiple users
- Added to the installation steps pipeline
- Installs FVM for current user, komodo user, and root user (if applicable)

**Enhanced Shell Integration:**

- Updated `setup_env.sh` to include FVM paths in PATH
- Added `.pub-cache/bin` and `.fvm/default/bin` to PATH
- Ensures PATH is configured on shell startup

### 2. Python Code Improvements

**Enhanced FVM Detection (`flutter_manager.py`):**

- Improved `is_fvm_installed()` to check multiple locations
- Checks common FVM installation paths for all users
- Temporarily adds FVM to PATH if found in non-standard locations

**Multi-User PATH Configuration (`dependency_manager.py`):**

- New `add_to_path_for_multiple_users()` method
- Safely adds PATH entries to shell profiles for:
  - Current user
  - Komodo user (`.bashrc`, `.zshrc`, `.profile`)
  - Root user (`.bashrc`, `.zshrc`, `.profile`)

**Updated Setup Process (`setup.py`):**

- Uses multi-user PATH configuration
- Ensures FVM paths are available for all users

### 3. Verification Tools

**FVM Verification Script (`scripts/verify_fvm.py`):**

- Comprehensive FVM installation checker
- Verifies FVM for multiple users
- Checks PATH configuration in shell profiles
- Tests FVM functionality and Flutter version listing

## Installation Locations

FVM is installed in the following locations:

### Per-User Locations

- `$HOME/.pub-cache/bin/fvm` - Main FVM binary
- `$HOME/.fvm/` - FVM Flutter versions storage
- `$HOME/.fvm/default/bin/` - Active Flutter version binaries

### Multi-User Support

- `/home/komodo/.pub-cache/bin/fvm`
- `/root/.pub-cache/bin/fvm`
- Current user's home directory

## PATH Configuration

The following paths are added to shell profiles:

1. `$HOME/.pub-cache/bin` - For FVM binary
2. `$HOME/.fvm/default/bin` - For active Flutter/Dart binaries

### Shell Profiles Updated

- `.bashrc`
- `.zshrc`
- `.profile`

## Usage

### Installation

```bash
# Run the install script (includes FVM installation)
curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | bash

# Or with root support
curl -fsSL https://raw.githubusercontent.com/takenagain/komodo-codex-env/main/install.sh | bash -s -- --allow-root
```

### Verification

```bash
# Verify FVM installation for all users
python3 ~/.komodo-codex-env/scripts/verify_fvm.py

# Check FVM status via the tool
kce-status

# List FVM Flutter versions
kce-fvm-list
```

### FVM Commands Available

```bash
# Direct FVM commands
fvm list                    # List installed Flutter versions
fvm install 3.32.0         # Install specific Flutter version
fvm use 3.32.0              # Set global Flutter version
fvm releases                # List available Flutter releases

# Through Komodo Codex Environment
kce-fvm-list               # List installed versions
kce-fvm-install 3.32.0     # Install version
kce-fvm-use 3.32.0         # Switch version
kce-fvm-releases           # List available releases

# Flutter/Dart with FVM
flutter --version          # Uses FVM Flutter
dart --version             # Uses FVM Dart
```

## Troubleshooting

### FVM Not Found

1. Restart your terminal to reload PATH
2. Run: `source ~/.bashrc` or `source ~/.zshrc`
3. Verify installation: `python3 ~/.komodo-codex-env/scripts/verify_fvm.py`
4. Re-run setup: `kce-full-setup`

### Permission Issues

```bash
# If running as root, use --allow-root flag
./install.sh --allow-root

# Ensure komodo user has proper permissions
sudo chown -R komodo:komodo /home/komodo/.pub-cache
sudo chown -R komodo:komodo /home/komodo/.fvm
```

### Manual FVM Installation

If automatic installation fails:

```bash
# Use official FVM installer
curl -fsSL https://fvm.app/install.sh | bash

# Add to PATH manually if needed
echo 'export PATH="$PATH:$HOME/.pub-cache/bin"' >> ~/.bashrc
source ~/.bashrc
```

## Benefits

1. **Multi-User Support:** FVM works for komodo user, root user, and current user
2. **Consistent Environment:** Same Flutter version management across all users
3. **Automatic Configuration:** PATH is properly configured during installation
4. **Verification Tools:** Built-in verification and troubleshooting
5. **Fallback Detection:** Finds FVM even if PATH is not properly configured
6. **Shell Integration:** Works with bash, zsh, and other common shells

## Technical Details

### Installation Process

1. Install script downloads and installs FVM using pub global activate
2. Configures PATH in shell profiles for all users
3. Python setup verifies and enhances FVM configuration
4. Verification script confirms proper installation

### Fallback Mechanisms

- Multiple FVM detection methods
- Common path checking
- Session PATH updates
- Bootstrap Flutter installation if needed

This fix ensures that FVM is reliably available in all user environments within the Komodo Codex Environment setup.
