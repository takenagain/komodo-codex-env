"""Command-line interface for the Komodo Codex Environment Setup Tool."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from .config import EnvironmentConfig
from .setup import EnvironmentSetup
from .documentation_manager import DocumentationManager
from .executor import CommandExecutor
from .dependency_manager import DependencyManager
from .flutter_manager import FlutterManager

console = Console()


@click.group()
@click.version_option()
def cli():
    """Komodo Codex Environment Setup Tool - Python Edition
    
    A comprehensive Flutter development environment setup tool with better
    maintainability and error handling than the original bash script.
    """
    pass


@cli.command()
@click.option("--flutter-version", default="stable", help="Flutter version to install")
@click.option("--install-method", type=click.Choice(["git", "precompiled"]), default="precompiled", help="Flutter installation method")
@click.option(
    "--install-type",
    type=click.Choice(["ALL", "KW", "KDF", "KDF-SDK"]),
    default="ALL",
    help="Installation type: ALL, KW, KDF, or KDF-SDK",
)
@click.option("--no-parallel", is_flag=True, help="Disable parallel execution")
@click.option("--platforms", default="web", help="Comma-separated list of platforms to setup (e.g., web,android,linux)")
@click.option("--no-git-fetch", is_flag=True, help="Skip fetching git branches")
@click.option("--no-docs", is_flag=True, help="Skip documentation fetching")
@click.option("--kdf-docs", is_flag=True, help="Fetch KDF API documentation")
@click.option("--max-time", default=300, help="Maximum execution time in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def setup(
    flutter_version, 
    install_method,
    install_type,
    no_parallel, 
    platforms, 
    no_git_fetch, 
    no_docs, 
    kdf_docs, 
    max_time,
    verbose
):
    """Run the complete Flutter environment setup."""
    
    # Create configuration
    config = EnvironmentConfig.from_environment()
    
    # Override with command line options
    config.flutter_version = flutter_version
    config.flutter_install_method = install_method
    config.install_type = install_type
    config.parallel_execution = not no_parallel
    config.platforms = [p.strip() for p in platforms.split(",")]
    config.fetch_all_remote_branches = not no_git_fetch
    config.should_fetch_agents_docs = not no_docs
    config.should_fetch_kdf_api_docs = kdf_docs
    config.max_execution_time = max_time
    
    if verbose:
        console.print(f"[blue]Configuration:[/blue]")
        console.print(f"  Flutter version: {config.flutter_version}")
        console.print(f"  Install method: {config.flutter_install_method}")
        console.print(f"  Install type: {config.install_type}")
        console.print(f"  Platforms: {', '.join(config.platforms)}")
        console.print(f"  Parallel execution: {config.parallel_execution}")
        console.print(f"  Max parallel jobs: {config.max_parallel_jobs}")
        console.print(f"  Fetch git branches: {config.fetch_all_remote_branches}")
        console.print(f"  Fetch documentation: {config.should_fetch_agents_docs}")
        console.print("")
    
    # Run setup
    setup_manager = EnvironmentSetup(config)
    
    try:
        success = asyncio.run(setup_manager.run_setup())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[red]Setup interrupted by user[/red]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Setup failed with unexpected error: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--target", type=click.Path(), default=".", help="Target directory for documentation")
@click.option("--no-agents", is_flag=True, help="Skip AGENTS.md")
@click.option("--kdf-docs", is_flag=True, help="Include KDF API documentation")
def fetch_docs(target, no_agents, kdf_docs):
    """Fetch documentation files only."""
    
    config = EnvironmentConfig.from_environment()
    config.should_fetch_agents_docs = not no_agents
    config.should_fetch_kdf_api_docs = kdf_docs
    
    executor = CommandExecutor()
    doc_manager = DocumentationManager(config, executor)
    
    try:
        # Fetch documentation
        documents = asyncio.run(doc_manager.fetch_all_documentation())
        
        if not documents:
            console.print("[yellow]No documentation was fetched[/yellow]")
            return
        
        # Save documentation
        target_path = Path(target).resolve()
        success = doc_manager.save_documentation(documents, target_path)
        
        if success:
            # Create combined documentation
            doc_manager.create_combined_documentation(documents, target_path)
            
            # Update git exclude
            doc_manager.update_git_exclude(target_path)
            
            console.print(f"[green]Documentation saved to {target_path}[/green]")
        else:
            console.print("[red]Failed to save documentation[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Documentation fetch failed: {e}[/red]")
        sys.exit(1)


@cli.command()
def check_deps():
    """Check system dependencies."""
    
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    
    # Required dependencies
    required_deps = ["curl", "git", "unzip", "xz-utils", "zip", "libglu1-mesa"]
    
    console.print("[blue]Checking system dependencies...[/blue]")
    
    # Get system info
    system_info = dep_manager.get_system_info()
    console.print(f"System: {system_info.get('os', 'Unknown')} {system_info.get('arch', 'Unknown')}")
    if system_info.get("distro"):
        console.print(f"Distribution: {system_info['distro']}")
    
    # Check package manager
    pm = dep_manager.detect_package_manager()
    if pm:
        console.print(f"Package manager: {pm}")
    else:
        console.print("[red]No supported package manager found[/red]")
    
    # Check dependencies
    results = dep_manager.check_dependencies(required_deps)
    
    console.print("\nDependency Status:")
    for dep, installed in results.items():
        status = "[green]✓[/green]" if installed else "[red]✗[/red]"
        console.print(f"  {status} {dep}")
    
    missing = [dep for dep, installed in results.items() if not installed]
    if missing:
        console.print(f"\n[yellow]Missing dependencies: {', '.join(missing)}[/yellow]")
        console.print("Run 'setup' command to install missing dependencies.")
    else:
        console.print("\n[green]All dependencies are installed![/green]")


@cli.command()
@click.option("--version", default=None, help="Flutter version to check/install")
def flutter_status(version):
    """Check Flutter installation status via FVM."""
    
    config = EnvironmentConfig.from_environment()
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    flutter_manager = FlutterManager(config, executor, dep_manager)
    
    console.print("[blue]Flutter Installation Status (via FVM)[/blue]")
    
    # Check if FVM is installed
    if not flutter_manager.is_fvm_installed():
        console.print("[red]✗ FVM is not installed[/red]")
        console.print("Run 'setup' command to install FVM and Flutter.")
        return
    
    console.print("[green]✓ FVM is installed[/green]")
    
    # Check if Flutter is installed via FVM
    if flutter_manager.is_flutter_installed():
        console.print("[green]✓ Flutter is installed via FVM[/green]")
        
        # Get version
        installed_version = flutter_manager.get_installed_version()
        if installed_version:
            console.print(f"  Active version: {installed_version}")
        
        # Check if version matches requested
        if version:
            if installed_version and installed_version != version:
                console.print(f"  [yellow]Requested version: {version}[/yellow]")
        elif config.flutter_version:
            if installed_version and installed_version != config.flutter_version:
                console.print(f"  [yellow]Config version: {config.flutter_version}[/yellow]")
        
        # List available versions
        available_versions = flutter_manager.list_available_versions()
        if available_versions:
            console.print(f"  Available versions: {len(available_versions)} total")
        
        # Check Flutter doctor
        console.print("\nRunning Flutter doctor...")
        try:
            result = executor.run_command("fvm flutter doctor", check=False)
            if result.returncode == 0:
                console.print("[green]✓ Flutter doctor passed[/green]")
            else:
                console.print("[yellow]⚠ Flutter doctor has warnings[/yellow]")
        except Exception as e:
            console.print(f"[red]Flutter doctor failed: {e}[/red]")
    
    else:
        console.print("[red]✗ Flutter is not installed via FVM[/red]")
        console.print("Run 'setup' command to install Flutter.")


@cli.command()
def update_script():
    """Check for and download script updates."""
    
    config = EnvironmentConfig.from_environment()
    executor = CommandExecutor()
    doc_manager = DocumentationManager(config, executor)
    
    console.print("[blue]Checking for script updates...[/blue]")
    
    latest_version = doc_manager.check_for_script_updates()
    
    if latest_version:
        console.print(f"[yellow]Update available: {latest_version}[/yellow]")
        
        if click.confirm("Download update?"):
            script_path = Path.home() / "komodo_flutter_codex_env_setup.sh"
            success = doc_manager.download_script_update(script_path)
            
            if success:
                console.print(f"[green]Updated script saved to {script_path}[/green]")
            else:
                console.print("[red]Failed to download update[/red]")
    else:
        console.print("[green]Script is up to date[/green]")


@cli.command()
def fvm_list():
    """List installed Flutter versions via FVM."""
    
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    config = EnvironmentConfig.from_environment()
    flutter_manager = FlutterManager(config, executor, dep_manager)
    
    if not flutter_manager.is_fvm_installed():
        console.print("[red]FVM is not installed[/red]")
        console.print("Run 'setup' command to install FVM.")
        return
    
    try:
        result = executor.run_command("fvm list", check=False)
        if result.returncode == 0:
            console.print("[blue]Installed Flutter versions:[/blue]")
            console.print(result.stdout)
        else:
            console.print("[yellow]No Flutter versions installed via FVM[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to list FVM versions: {e}[/red]")


@cli.command()
@click.argument("version")
def fvm_install(version):
    """Install a specific Flutter version via FVM."""
    
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    config = EnvironmentConfig.from_environment()
    flutter_manager = FlutterManager(config, executor, dep_manager)
    
    if not flutter_manager.is_fvm_installed():
        console.print("[red]FVM is not installed[/red]")
        console.print("Run 'setup' command to install FVM.")
        return
    
    console.print(f"[blue]Installing Flutter {version} via FVM...[/blue]")
    
    try:
        result = executor.run_command(f"fvm install {version}", timeout=600, check=False)
        if result.returncode == 0:
            console.print(f"[green]Flutter {version} installed successfully![/green]")
        else:
            console.print(f"[red]Failed to install Flutter {version}[/red]")
    except Exception as e:
        console.print(f"[red]Installation failed: {e}[/red]")


@cli.command()
@click.argument("version")
def fvm_use(version):
    """Set global Flutter version via FVM."""
    
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    config = EnvironmentConfig.from_environment()
    flutter_manager = FlutterManager(config, executor, dep_manager)
    
    if not flutter_manager.is_fvm_installed():
        console.print("[red]FVM is not installed[/red]")
        console.print("Run 'setup' command to install FVM.")
        return
    
    success = flutter_manager.switch_version(version)
    if success:
        console.print(f"[green]Now using Flutter {version} globally[/green]")
    else:
        console.print(f"[red]Failed to switch to Flutter {version}[/red]")


@cli.command()
def fvm_releases():
    """List available Flutter releases via FVM."""
    
    executor = CommandExecutor()
    dep_manager = DependencyManager(executor)
    config = EnvironmentConfig.from_environment()
    flutter_manager = FlutterManager(config, executor, dep_manager)
    
    if not flutter_manager.is_fvm_installed():
        console.print("[red]FVM is not installed[/red]")
        console.print("Run 'setup' command to install FVM.")
        return
    
    try:
        result = executor.run_command("fvm releases", check=False)
        if result.returncode == 0:
            console.print("[blue]Available Flutter releases:[/blue]")
            console.print(result.stdout)
        else:
            console.print("[red]Failed to fetch Flutter releases[/red]")
    except Exception as e:
        console.print(f"[red]Failed to fetch releases: {e}[/red]")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
