"""Configuration management for the Komodo Codex Environment Setup Tool."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from packaging.version import Version


@dataclass
class EnvironmentConfig:
    """Configuration settings for the environment setup."""

    # Script configuration
    script_version: str = "1.3.0"
    auto_update_script: bool = False
    skip_recursive_update: bool = False
    max_execution_time: int = 300  # 5 minutes in seconds

    # Parallel execution settings
    parallel_execution: bool = True
    max_parallel_jobs: Optional[int] = None

    # Flutter configuration
    flutter_version: str = "3.32.0"
    flutter_install_method: str = "precompiled"  # "git" or "precompiled"
    platforms: List[str] = field(default_factory=lambda: ["web"])

    # Android configuration
    install_android_sdk: bool = True
    android_api_level: str = "34"
    android_build_tools_version: str = "34.0.0"

    # Git configuration
    fetch_all_remote_branches: bool = True
    remote_base_url: str = "https://github.com/KomodoPlatform"

    # Documentation fetching
    should_fetch_agents_docs: bool = True
    should_fetch_kdf_api_docs: bool = False

    # URLs
    gist_base_url: str = "https://gist.githubusercontent.com/CharlVS/14233fff7e9b3d66a7268d578cc34b36/raw"
    kdf_api_docs_url: str = "https://raw.githubusercontent.com/KomodoPlatform/komodo-docs-mdx/refs/heads/dev/data-for-gpts/komodefi-api/all-api-content.txt"

    # Paths
    home_dir: Path = field(default_factory=lambda: Path.home())
    flutter_dir: Optional[Path] = None
    fvm_dir: Optional[Path] = None
    android_home: Optional[Path] = None
    initial_dir: Optional[Path] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.max_parallel_jobs is None:
            # Calculate based on CPU cores, minimum 1
            import psutil
            cpu_count = psutil.cpu_count(logical=False) or 1
            self.max_parallel_jobs = max(1, cpu_count // 2)

        if self.flutter_dir is None:
            self.flutter_dir = self.home_dir / "flutter"

        if self.fvm_dir is None:
            self.fvm_dir = self.home_dir / ".fvm"

        if self.initial_dir is None:
            self.initial_dir = Path.cwd()

        if self.android_home is None:
            self.android_home = self.home_dir / "Android" / "Sdk"

    @property
    def script_gist_url(self) -> str:
        """Get the script gist URL."""
        return f"{self.gist_base_url}/komodo_flutter_codex_env_setup.sh"

    @property
    def agents_gist_url(self) -> str:
        """Get the agents documentation gist URL."""
        return f"{self.gist_base_url}/AGENTS.md"

    @property
    def flutter_bin_dir(self) -> Path:
        """Get the Flutter bin directory (via FVM default)."""
        return self.fvm_dir / "default" / "bin"

    @property
    def pub_cache_bin_dir(self) -> Path:
        """Get the pub cache bin directory."""
        return self.home_dir / ".pub-cache" / "bin"

    @property
    def fvm_flutter_bin(self) -> Path:
        """Get the FVM Flutter binary path."""
        return self.fvm_dir / "default" / "bin" / "flutter"

    @classmethod
    def from_environment(cls) -> "EnvironmentConfig":
        """Create configuration from environment variables."""
        config = cls()

        # Override with environment variables if present
        config.auto_update_script = os.getenv("AUTO_UPDATE_SCRIPT", "false").lower() == "true"
        config.skip_recursive_update = os.getenv("SKIP_RECURSIVE_UPDATE", "false").lower() == "true"
        config.parallel_execution = os.getenv("PARALLEL_EXECUTION", "true").lower() == "true"
        config.flutter_install_method = os.getenv("FLUTTER_INSTALL_METHOD", "precompiled")
        config.fetch_all_remote_branches = os.getenv("FETCH_ALL_REMOTE_BRANCHES", "true").lower() == "true"
        config.should_fetch_agents_docs = os.getenv("SHOULD_FETCH_AGENTS_DOCS", "true").lower() == "true"
        config.should_fetch_kdf_api_docs = os.getenv("SHOULD_FETCH_KDF_API_DOCS", "false").lower() == "true"
        config.install_android_sdk = os.getenv("INSTALL_ANDROID_SDK", "true").lower() == "true"

        # Handle platforms
        platforms_env = os.getenv("PLATFORMS")
        if platforms_env:
            config.platforms = [p.strip() for p in platforms_env.split(",")]

        # Handle max parallel jobs
        max_jobs_env = os.getenv("MAX_PARALLEL_JOBS")
        if max_jobs_env and max_jobs_env.isdigit():
            config.max_parallel_jobs = int(max_jobs_env)

        return config

    def get_flutter_version(self) -> Version:
        """Get the Flutter version as a Version object."""
        return Version(self.flutter_version)

    def get_shell_profile(self) -> Path:
        """Get the appropriate shell profile file."""
        shell = os.getenv("SHELL", "")

        if "zsh" in shell:
            return self.home_dir / ".zshrc"
        elif "bash" in shell:
            return self.home_dir / ".bashrc"
        else:
            return self.home_dir / ".profile"
