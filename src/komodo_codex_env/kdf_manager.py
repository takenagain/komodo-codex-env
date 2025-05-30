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
                self.executor.run_command("bash -c 'source $HOME/.cargo/env'", check=False)
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
