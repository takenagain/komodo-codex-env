from sys import exit
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
from .android_manager import AndroidManager
from .documentation_manager import DocumentationManager
from .kdf_manager import KdfManager

console = Console()


class EnvironmentSetup:
    """Main orchestrator for the Flutter environment setup."""

    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.start_time = time.time()

        # Initialize components
        self.executor = CommandExecutor(
            parallel_execution=config.parallel_execution,
            max_workers=config.max_parallel_jobs if config.max_parallel_jobs else 4
        )
        self.dep_manager = DependencyManager(self.executor)
        self.git_manager = GitManager(self.executor)
        self.flutter_manager = FlutterManager(config, self.executor, self.dep_manager)
        self.android_manager = AndroidManager(config, self.executor, self.dep_manager)
        self.doc_manager = DocumentationManager(config, self.executor)
        self.kdf_manager = KdfManager(config, self.executor, self.dep_manager)

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

            # Phase 3: Flutter and Android SDK installation (parallel)
            if self.config.install_type in ("ALL", "KW", "KDF-SDK"):
                if not await self._setup_flutter_and_android():
                    return False
            else:
                console.print("[blue]Skipping Flutter and Android installation[/blue]")

            # Phase 4: Environment configuration
            if self.config.install_type in ("ALL", "KW"):
                if not await self._setup_environment():
                    return False
            else:
                console.print("[blue]Skipping Flutter environment configuration[/blue]")

            # Phase 5: Documentation (parallel with project setup)
            if not await self._setup_documentation():
                return False

            # Phase 6: KDF dependencies
            if self.config.install_type in ("ALL", "KDF", "KDF-SDK"):
                if not await self._setup_kdf_dependencies():
                    return False

            # Phase 7: Project setup
            if self.config.install_type in ("ALL", "KW"):
                if not await self._setup_project():
                    return False
            else:
                console.print("[blue]Skipping Flutter project setup[/blue]")

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
            success = self.git_manager.fetch_all_branches()
            if success:
                console.print("[green]✓ Git branches fetched[/green]")
            else:
                console.print("[yellow]⚠ Git fetch completed with warnings[/yellow]")

        return True

    async def _setup_flutter_and_android(self) -> bool:
        """Set up Flutter SDK and Android SDK in parallel."""
        console.print("[bold blue]Phase 3: Flutter and Android SDK Installation[/bold blue]")

        if self.config.parallel_execution:
            # Run Flutter and Android setup in parallel
            tasks = []

            # Flutter setup task
            async def setup_flutter():
                success = self.flutter_manager.install_flutter()
                if not success:
                    console.print("[red]✗ Flutter installation failed[/red]")
                    return False

                success = self.flutter_manager.configure_flutter()
                if success:
                    console.print("[green]✓ Flutter installed and configured[/green]")
                else:
                    console.print("[yellow]⚠ Flutter installed but configuration had issues[/yellow]")
                return True

            # Android setup task
            async def setup_android():
                if not self.config.install_android_sdk:
                    console.print("[blue]Android SDK installation skipped[/blue]")
                    return True

                # Check if android is in platforms list
                if "android" not in self.config.platforms:
                    console.print("[blue]Android not in target platforms, skipping SDK installation[/blue]")
                    return True

                # Run Android SDK installation in a thread since it's not async
                import asyncio
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, self.android_manager.install_android_sdk)

                if success:
                    console.print("[green]✓ Android SDK installed and configured[/green]")
                else:
                    console.print("[yellow]⚠ Android SDK installation had issues[/yellow]")
                return success

            tasks.append(setup_flutter())
            tasks.append(setup_android())

            # Wait for both tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            flutter_success = results[0] if not isinstance(results[0], Exception) else False
            android_success = results[1] if not isinstance(results[1], Exception) else True  # Default to True if skipped

            if isinstance(results[0], Exception):
                console.print(f"[red]Flutter setup failed: {results[0]}[/red]")
                flutter_success = False

            if isinstance(results[1], Exception):
                console.print(f"[yellow]Android setup failed: {results[1]}[/yellow]")
                android_success = True  # Non-critical failure

            return flutter_success == True  # noqa: E712
        else:
            # Sequential execution
            flutter_success = await self._setup_flutter_sequential()
            if not flutter_success:
                return False

            android_success = await self._setup_android_sequential()
            # Android failure is not critical

            return True

    async def _setup_flutter_sequential(self) -> bool:
        """Set up Flutter SDK sequentially."""
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

    async def _setup_android_sequential(self) -> bool:
        """Set up Android SDK sequentially."""
        if not self.config.install_android_sdk:
            console.print("[blue]Android SDK installation skipped[/blue]")
            return True

        # Check if android is in platforms list
        if "android" not in self.config.platforms:
            console.print("[blue]Android not in target platforms, skipping SDK installation[/blue]")
            return True

        # Run Android SDK installation
        import asyncio
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, self.android_manager.install_android_sdk)

        if success:
            console.print("[green]✓ Android SDK installed and configured[/green]")
        else:
            console.print("[yellow]⚠ Android SDK installation had issues[/yellow]")
        return success

    async def _setup_environment(self) -> bool:
        """Set up environment variables and PATH."""
        console.print("[bold blue]Phase 4: Environment Configuration[/bold blue]")

        profile_path = self.config.get_shell_profile()
        console.print(f"[blue]Shell profile: {profile_path}[/blue]")

        # Add Flutter to PATH for all users
        flutter_bin_success = self.dep_manager.add_to_path_for_multiple_users(
            str(self.config.flutter_bin_dir)
        )

        # Add pub cache to PATH for all users
        pub_cache_success = self.dep_manager.add_to_path_for_multiple_users(
            str(self.config.pub_cache_bin_dir)
        )

        if flutter_bin_success and pub_cache_success:
            console.print("[green]✓ Environment variables configured for all users[/green]")
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
            success = False
            if target_dir and target_dir.exists():
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

    async def _setup_kdf_dependencies(self) -> bool:
        """Install Komodo DeFi Framework dependencies."""
        console.print("[bold blue]Phase 6: KDF Dependencies[/bold blue]")

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, self.kdf_manager.install_dependencies)
        return success

    async def _setup_project(self) -> bool:
        """Set up the Flutter project."""
        console.print("[bold blue]Phase 7: Project Setup[/bold blue]")

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

        if self.config.install_android_sdk and "android" in self.config.platforms:
            android_info = self.android_manager.get_android_info()
            if android_info.get("status") == "installed":
                summary.append(f"[blue]Android SDK: {android_info.get('android_home', 'Installed')}[/blue]")

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

        if self.config.install_android_sdk and "android" in self.config.platforms:
            next_steps.extend([
                "",
                "Android development:",
                "  flutter doctor --android-licenses  - Accept Android licenses",
                "  flutter devices                    - List available devices",
                "  flutter emulators                  - List available emulators",
            ])

        console.print(Panel.fit(
            "\n".join(next_steps),
            title="Next Steps",
            border_style="blue"
        ))
