"""Komodo DeFi Framework dependency installer."""

from pathlib import Path
from rich.console import Console

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager

console = Console()


class KdfManager:
    """Manage Komodo DeFi Framework dependencies."""

    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor, dep_manager: DependencyManager):
        self.config = config
        self.executor = executor
        self.dep_manager = dep_manager
        self.fetch_script = Path(__file__).resolve().parents[2] / "scripts" / "fetch_params.sh"

    def install_dependencies(self) -> bool:
        """Install KDF dependencies and fetch Zcash params."""
        console.print("[bold blue]Installing KDF dependencies...[/bold blue]")

        packages = ["docker.io", "libudev-dev", "protobuf-compiler"]
        success = self.dep_manager.install_dependencies(packages)
        if not success:
            console.print("[red]Failed to install required packages[/red]")
            return False

        # Install Rust toolchain if not available
        if not self.executor.check_command_exists("rustc"):
            console.print("[blue]Installing Rust toolchain via rustup...[/blue]")
            try:
                self.executor.run_command(
                    "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
                    check=False,
                    timeout=600,
                )
                self._update_shell_configs()
            except Exception as e:
                console.print(f"[red]Failed to install Rust: {e}[/red]")
                return False
        else:
            console.print("[green]Rust already installed[/green]")

        if self.fetch_script.exists():
            try:
                self.executor.run_command(f"bash {self.fetch_script}", check=False, timeout=900)
            except Exception as e:
                console.print(f"[red]Failed to fetch ZCash parameters: {e}[/red]")
                return False
        else:
            console.print(f"[yellow]fetch_params.sh not found at {self.fetch_script}[/yellow]")
            return False

        console.print("[green]✓ KDF dependencies installed successfully[/green]")
        return True

    def _update_shell_configs(self) -> None:
        """Update shell configuration files to include Cargo environment."""
        home = Path.home()
        cargo_env_line = "source $HOME/.cargo/env"
        
        # List of shell config files to update
        shell_configs = [
            home / ".bashrc",
            home / ".zshrc", 
            home / ".profile",
            home / ".bash_profile"
        ]
        
        # Also check for fish shell config
        fish_config = home / ".config" / "fish" / "config.fish"
        fish_env_line = "source $HOME/.cargo/env.fish"
        
        for config_file in shell_configs:
            if config_file.exists():
                try:
                    # Check if the line already exists
                    content = config_file.read_text()
                    if cargo_env_line not in content:
                        self.executor.run_command(
                            f"echo '{cargo_env_line}' >> {config_file}",
                            check=False
                        )
                        console.print(f"[green]Updated {config_file.name}[/green]")
                    else:
                        console.print(f"[yellow]{config_file.name} already configured[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]Could not update {config_file.name}: {e}[/yellow]")
        
        # Handle fish shell separately
        if fish_config.exists():
            try:
                content = fish_config.read_text()
                if fish_env_line not in content:
                    self.executor.run_command(
                        f"echo '{fish_env_line}' >> {fish_config}",
                        check=False
                    )
                    console.print(f"[green]Updated fish config[/green]")
                else:
                    console.print(f"[yellow]Fish config already configured[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Could not update fish config: {e}[/yellow]")
        
        # Create fish env file if fish config exists but env file doesn't
        fish_env_file = home / ".cargo" / "env.fish"
        if fish_config.exists() and not fish_env_file.exists():
            try:
                self.executor.run_command(
                    f"test -f {home}/.cargo/env && "
                    f"sed 's/export /set -gx /g; s/=/ /g' {home}/.cargo/env > {fish_env_file}",
                    check=False
                )
            except Exception as e:
                console.print(f"[yellow]Could not create fish env file: {e}[/yellow]")
