"""Main setup orchestrator that coordinates all components."""

import asyncio
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager
from .git_manager import GitManager
from .flutter_manager import FlutterManager
from .documentation_manager import DocumentationManager

console = Console()


class EnvironmentSetup:
    """Main orchestrator for the Flutter environment setup."""
    
    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.start_time = time.time()
        
        # Initialize components
        self.executor = CommandExecutor(
            parallel_execution=config.parallel_execution,
            max_workers=config.max_parallel_jobs
        )
        self.dep_manager = DependencyManager(self.executor)
        self.git_manager = GitManager(self.executor)
        self.flutter_manager = FlutterManager(config, self.executor, self.dep_manager)
        self.doc_manager = DocumentationManager(config, self.executor)
    
    async def run_setup(self) -> bool:
        """Run the complete environment setup."""
        console.print(Panel.fit(
            f"[bold blue]Komodo Codex Environment Setup v{self.config.script_version}[/bold blue]\n"
            f"Setting up Flutter {self.config.flutter_version} environment",
            title="Environment Setup"
        ))
        
        try:
            # Phase 1: System dependencies
            if not await self._setup_system_dependencies():
                return False
            
            # Phase 2: Git operations
            await self._setup_git_operations()
            
            # Phase 3: Flutter installation
            if not await self._setup_flutter():
                return False
            
            # Phase 4: Environment configuration
            if not await self._setup_environment():
                return False
            
            # Phase 5: Documentation (parallel with project setup)
            if not await self._setup_documentation():
                return False
            
            # Phase 6: Project setup
            if not await self._setup_project():
                return False
            
            self._print_completion_summary()
            return True
            
        except Exception as e:
            console.print(f"[red]Setup failed with error: {e}[/red]")
            return False
    
    async def _setup_system_dependencies(self) -> bool:
        """Set up system dependencies."""
        console.print("[bold blue]Phase 1: System Dependencies[/bold blue]")
        
        # Required dependencies - platform agnostic names
        required_deps = ["curl", "git", "unzip", "xz-utils", "zip"]
        
        # Check system info
        system_info = self.dep_manager.get_system_info()
        console.print(f"[blue]System: {system_info.get('os', 'Unknown')} {system_info.get('arch', 'Unknown')}[/blue]")
        
        if system_info.get("distro"):
            console.print(f"[blue]Distribution: {system_info['distro']}[/blue]")
        
        # Add platform-specific dependencies
        if system_info.get("os") == "Linux":
            required_deps.extend(["libglu1-mesa", "build-essential"])
        
        # Add Dart for FVM
        required_deps.append("dart")
        
        # Install dependencies
        success = self.dep_manager.install_dependencies(required_deps)
        
        if success:
            console.print("[green]✓ System dependencies installed[/green]")
        else:
            console.print("[red]✗ Failed to install system dependencies[/red]")
        
        return success
    
    async def _setup_git_operations(self) -> bool:
        """Set up Git operations."""
        console.print("[bold blue]Phase 2: Git Operations[/bold blue]")
        
        if not self.git_manager.is_git_repo():
            console.print("[yellow]Not in a Git repository, skipping Git operations[/yellow]")
            return True
        
        repo_name = self.git_manager.get_repo_name()
        console.print(f"[blue]Repository: {repo_name}[/blue]")
        
        if self.config.fetch_all_remote_branches:
            # Set up remote
            remote_url = f"{self.config.remote_base_url}/{repo_name}.git"
            self.git_manager.add_remote("origin", remote_url)
            
            # Fetch all branches
            success = self.git_manager.fetch_all_branches()
            if success:
                console.print("[green]✓ Git branches fetched[/green]")
            else:
                console.print("[yellow]⚠ Git fetch completed with warnings[/yellow]")
        
        return True
    
    async def _setup_flutter(self) -> bool:
        """Set up Flutter SDK."""
        console.print("[bold blue]Phase 3: Flutter Installation[/bold blue]")
        
        # Install Flutter
        success = self.flutter_manager.install_flutter()
        if not success:
            console.print("[red]✗ Flutter installation failed[/red]")
            return False
        
        # Configure Flutter
        success = self.flutter_manager.configure_flutter()
        if success:
            console.print("[green]✓ Flutter installed and configured[/green]")
        else:
            console.print("[yellow]⚠ Flutter installed but configuration had issues[/yellow]")
        
        return True
    
    async def _setup_environment(self) -> bool:
        """Set up environment variables and PATH."""
        console.print("[bold blue]Phase 4: Environment Configuration[/bold blue]")
        
        profile_path = self.config.get_shell_profile()
        console.print(f"[blue]Shell profile: {profile_path}[/blue]")
        
        # Add Flutter to PATH
        flutter_bin_success = self.dep_manager.add_to_path(
            str(self.config.flutter_bin_dir), 
            profile_path
        )
        
        # Add pub cache to PATH
        pub_cache_success = self.dep_manager.add_to_path(
            str(self.config.pub_cache_bin_dir),
            profile_path
        )
        
        if flutter_bin_success and pub_cache_success:
            console.print("[green]✓ Environment variables configured[/green]")
        else:
            console.print("[yellow]⚠ Environment configuration had issues[/yellow]")
        
        return True
    
    async def _setup_documentation(self) -> bool:
        """Set up documentation files."""
        console.print("[bold blue]Phase 5: Documentation[/bold blue]")
        
        try:
            # Fetch documentation
            documents = await self.doc_manager.fetch_all_documentation()
            
            if not documents:
                console.print("[yellow]No documentation was fetched[/yellow]")
                return True
            
            # Save documentation
            target_dir = self.config.initial_dir
            success = self.doc_manager.save_documentation(documents, target_dir)
            
            if success:
                # Create combined documentation
                self.doc_manager.create_combined_documentation(documents, target_dir)
                
                # Update git exclude
                self.doc_manager.update_git_exclude(target_dir)
                
                console.print(f"[green]✓ Documentation saved ({len(documents)} files)[/green]")
            else:
                console.print("[yellow]⚠ Documentation setup had issues[/yellow]")
            
            return success
            
        except Exception as e:
            console.print(f"[yellow]Documentation setup failed: {e}[/yellow]")
            return False
    
    async def _setup_project(self) -> bool:
        """Set up the Flutter project."""
        console.print("[bold blue]Phase 6: Project Setup[/bold blue]")
        
        project_path = self.config.initial_dir
        
        # Check if this is a Flutter project
        pubspec_file = project_path / "pubspec.yaml"
        if not pubspec_file.exists():
            console.print("[yellow]No pubspec.yaml found, skipping Flutter project setup[/yellow]")
            return True
        
        try:
            # Get dependencies
            console.print("[blue]Getting Flutter dependencies...[/blue]")
            result = self.executor.run_command(
                "fvm flutter pub get",
                cwd=project_path,
                check=False
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Dependencies installed[/green]")
            else:
                console.print("[yellow]⚠ Dependency installation had issues[/yellow]")
            
            # Run build_runner
            console.print("[blue]Running build_runner...[/blue]")
            result = self.executor.run_command(
                "fvm dart run build_runner build --delete-conflicting-outputs",
                cwd=project_path,
                check=False,
                timeout=120
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Code generation completed[/green]")
            else:
                console.print("[yellow]⚠ Code generation had issues[/yellow]")
            
            # Build project for configured platforms
            if self.config.platforms:
                console.print(f"[blue]Building for platforms: {', '.join(self.config.platforms)}[/blue]")
                build_success = self.flutter_manager.build_project(project_path, self.config.platforms)
                
                if build_success:
                    console.print("[green]✓ Project builds completed[/green]")
                else:
                    console.print("[yellow]⚠ Some builds failed (expected for initial setup)[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Project setup failed: {e}[/yellow]")
            return False
    
    def _print_completion_summary(self):
        """Print completion summary."""
        elapsed_time = time.time() - self.start_time
        percentage = (elapsed_time / self.config.max_execution_time) * 100
        
        summary = [
            f"[green]✓ Environment setup completed successfully![/green]",
            f"[blue]Execution time: {elapsed_time:.1f}s ({percentage:.1f}% of max time)[/blue]",
            f"[blue]Flutter version: {self.config.flutter_version} (via FVM)[/blue]",
            f"[blue]Installation method: FVM[/blue]",
        ]
        
        if self.config.platforms:
            summary.append(f"[blue]Configured platforms: {', '.join(self.config.platforms)}[/blue]")
        
        console.print(Panel.fit(
            "\n".join(summary),
            title="Setup Complete",
            border_style="green"
        ))
        
        # Print next steps
        next_steps = [
            "To use Flutter in your current session:",
            f"  source {self.config.get_shell_profile()}",
            "",
            "Or restart your terminal to apply PATH changes.",
            "",
            "Verify installation with:",
            "  fvm flutter doctor",
            "",
            "FVM commands:",
            "  fvm list          - List installed Flutter versions",
            "  fvm global <ver>  - Set global Flutter version",
            "  fvm use <ver>     - Use Flutter version for current project",
        ]
        
        console.print(Panel.fit(
            "\n".join(next_steps),
            title="Next Steps",
            border_style="blue"
        ))
