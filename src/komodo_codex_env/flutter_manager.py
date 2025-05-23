"""Flutter SDK installation and management using FVM (Flutter Version Management)."""

import json
import subprocess
from pathlib import Path
from typing import Optional, List
from packaging.version import Version
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager

console = Console()


class FlutterManager:
    """Manages Flutter SDK installation and configuration using FVM."""
    
    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor, dep_manager: DependencyManager):
        self.config = config
        self.executor = executor
        self.dep_manager = dep_manager
        self.fvm_home = self.config.home_dir / ".fvm"
        self.fvm_bin = self.fvm_home / "default" / "bin" / "flutter"
        
    def is_fvm_installed(self) -> bool:
        """Check if FVM is installed."""
        return self.executor.check_command_exists("fvm")
    
    def install_fvm(self) -> bool:
        """Install FVM using various methods."""
        if self.is_fvm_installed():
            console.print("[green]FVM is already installed[/green]")
            return True
        
        console.print("[blue]Installing FVM (Flutter Version Management)...[/blue]")
        
        # Try different installation methods based on the system
        system_info = self.dep_manager.get_system_info()
        os_name = system_info.get("os", "").lower()
        
        try:
            if "darwin" in os_name:
                # macOS - try Homebrew first, then pub global
                if self.executor.check_command_exists("brew"):
                    console.print("[blue]Installing FVM via Homebrew...[/blue]")
                    try:
                        self.executor.run_command("brew tap leoafarias/fvm")
                        self.executor.run_command("brew install fvm")
                        if self.is_fvm_installed():
                            return True
                    except Exception:
                        console.print("[yellow]Homebrew installation failed, trying pub global...[/yellow]")
            
            # Universal method - pub global activate
            console.print("[blue]Installing FVM via pub global activate...[/blue]")
            
            # First ensure we have Dart/Flutter pub available
            if not self.executor.check_command_exists("dart") and not self.executor.check_command_exists("flutter"):
                # Install Flutter first via git as a bootstrap
                console.print("[blue]Installing Flutter bootstrap for FVM...[/blue]")
                bootstrap_dir = self.config.home_dir / ".flutter_bootstrap"
                if not self._install_flutter_bootstrap(bootstrap_dir):
                    return False
                
                # Add bootstrap to PATH temporarily
                import os
                current_path = os.environ.get("PATH", "")
                os.environ["PATH"] = f"{bootstrap_dir / 'bin'}:{current_path}"
            
            # Install FVM via pub global
            result = self.executor.run_command(
                "dart pub global activate fvm",
                timeout=300,
                check=False
            )
            
            if result.returncode != 0:
                # Try with flutter pub instead
                result = self.executor.run_command(
                    "flutter pub global activate fvm",
                    timeout=300,
                    check=False
                )
            
            if result.returncode == 0:
                # Add pub cache to PATH
                pub_cache_bin = self.config.pub_cache_bin_dir
                self.dep_manager.add_to_path(str(pub_cache_bin), self.config.get_shell_profile())
                
                # Reload PATH for current session
                import os
                current_path = os.environ.get("PATH", "")
                if str(pub_cache_bin) not in current_path:
                    os.environ["PATH"] = f"{pub_cache_bin}:{current_path}"
                
                console.print("[green]FVM installed successfully via pub global![/green]")
                return True
            else:
                console.print("[red]Failed to install FVM via pub global[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]FVM installation failed: {e}[/red]")
            return False
    
    def _install_flutter_bootstrap(self, bootstrap_dir: Path) -> bool:
        """Install a minimal Flutter bootstrap for FVM installation."""
        try:
            if bootstrap_dir.exists():
                import shutil
                shutil.rmtree(bootstrap_dir)
            
            console.print("[blue]Cloning Flutter bootstrap...[/blue]")
            result = self.executor.run_command(
                f"git clone --depth 1 --branch stable https://github.com/flutter/flutter.git {bootstrap_dir}",
                timeout=300,
                check=False
            )
            
            if result.returncode != 0:
                console.print("[red]Failed to clone Flutter bootstrap[/red]")
                return False
            
            # Run flutter doctor once to initialize
            result = self.executor.run_command(
                f"{bootstrap_dir / 'bin' / 'flutter'} doctor",
                timeout=120,
                check=False
            )
            
            return True
            
        except Exception as e:
            console.print(f"[red]Flutter bootstrap installation failed: {e}[/red]")
            return False
    
    def is_flutter_installed(self) -> bool:
        """Check if Flutter is installed via FVM."""
        if not self.is_fvm_installed():
            return False
        
        try:
            result = self.executor.run_command(
                "fvm flutter --version",
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_installed_version(self) -> Optional[str]:
        """Get the currently active Flutter version via FVM."""
        if not self.is_flutter_installed():
            return None
        
        try:
            # Try to get version from FVM list
            result = self.executor.run_command(
                "fvm list",
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '→' in line or '*' in line:  # Active version marker
                        # Extract version number
                        parts = line.split()
                        for part in parts:
                            if part.replace('.', '').replace('-', '').replace('+', '').replace('beta', '').replace('dev', '').replace('rc', '').isdigit() or any(char.isdigit() for char in part):
                                if part not in ['→', '*']:
                                    return part
            
            # Fallback to flutter --version
            result = self.executor.run_command(
                "fvm flutter --version --machine",
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                version_info = json.loads(result.stdout)
                return version_info.get("frameworkVersion", None)
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not determine Flutter version: {e}[/yellow]")
        
        return None
    
    def list_available_versions(self) -> List[str]:
        """List available Flutter versions."""
        if not self.is_fvm_installed():
            return []
        
        try:
            result = self.executor.run_command(
                "fvm releases",
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                versions = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('Flutter') and not line.startswith('---'):
                        # Extract version from line
                        parts = line.split()
                        if parts:
                            version = parts[0]
                            if version.replace('.', '').replace('-', '').replace('+', '')[0].isdigit():
                                versions.append(version)
                return versions
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not list Flutter versions: {e}[/yellow]")
        
        return []
    
    def install_flutter(self) -> bool:
        """Install Flutter using FVM."""
        # First ensure FVM is installed
        if not self.install_fvm():
            console.print("[red]Cannot install Flutter without FVM[/red]")
            return False
        
        console.print(f"[blue]Installing Flutter {self.config.flutter_version} via FVM...[/blue]")
        
        try:
            # Install the specified Flutter version
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Installing Flutter {self.config.flutter_version}...", total=None)
                
                result = self.executor.run_command(
                    f"fvm install {self.config.flutter_version}",
                    timeout=600,  # 10 minutes timeout
                    check=False
                )
                
                progress.update(task, completed=True)
            
            if result.returncode != 0:
                console.print(f"[red]Failed to install Flutter {self.config.flutter_version}[/red]")
                return False
            
            # Set as global default
            console.print(f"[blue]Setting Flutter {self.config.flutter_version} as global default...[/blue]")
            result = self.executor.run_command(
                f"fvm global {self.config.flutter_version}",
                check=False
            )
            
            if result.returncode != 0:
                console.print("[yellow]Warning: Could not set Flutter as global default[/yellow]")
            
            # Verify installation
            if not self.is_flutter_installed():
                console.print("[red]Flutter installation verification failed[/red]")
                return False
            
            console.print(f"[green]Flutter {self.config.flutter_version} installed successfully via FVM![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Flutter installation failed: {e}[/red]")
            return False
    
    def configure_flutter(self) -> bool:
        """Configure Flutter after installation."""
        if not self.is_flutter_installed():
            console.print("[red]Flutter is not installed[/red]")
            return False
        
        try:
            console.print("[blue]Configuring Flutter...[/blue]")
            
            # Disable analytics
            self.executor.run_command("fvm flutter config --no-analytics")
            
            # Enable platforms based on configuration
            for platform in self.config.platforms:
                if platform == "web":
                    self.executor.run_command("fvm flutter config --enable-web")
                elif platform == "linux":
                    self.executor.run_command("fvm flutter config --enable-linux-desktop")
                elif platform == "macos":
                    self.executor.run_command("fvm flutter config --enable-macos-desktop")
                elif platform == "windows":
                    self.executor.run_command("fvm flutter config --enable-windows-desktop")
            
            # Pre-cache for configured platforms
            console.print(f"[blue]Pre-caching Flutter assets for {', '.join(self.config.platforms)}...[/blue]")
            precache_args = []
            
            if "web" in self.config.platforms:
                precache_args.append("--web")
            if "android" in self.config.platforms:
                precache_args.append("--android")
            if "ios" in self.config.platforms:
                precache_args.append("--ios")
            if "linux" in self.config.platforms:
                precache_args.append("--linux")
            if "macos" in self.config.platforms:
                precache_args.append("--macos")
            if "windows" in self.config.platforms:
                precache_args.append("--windows")
            
            # Add exclusions for platforms not in use
            all_platforms = ["android", "ios", "fuchsia", "linux", "macos", "windows", "web"]
            for platform in all_platforms:
                if platform not in self.config.platforms:
                    precache_args.append(f"--no-{platform}")
            
            if precache_args:
                self.executor.run_command(
                    f"fvm flutter precache {' '.join(precache_args)}",
                    timeout=300
                )
            
            # Run Flutter doctor
            console.print("[blue]Running Flutter doctor...[/blue]")
            result = self.executor.run_command(
                "fvm flutter doctor --no-analytics",
                timeout=60,
                check=False
            )
            
            if result.returncode != 0:
                console.print("[yellow]Flutter doctor completed with warnings[/yellow]")
            
            # Add FVM flutter to PATH
            self._setup_fvm_path()
            
            return True
            
        except Exception as e:
            console.print(f"[red]Flutter configuration failed: {e}[/red]")
            return False
    
    def _setup_fvm_path(self) -> bool:
        """Set up FVM Flutter in PATH."""
        try:
            # Add FVM default bin to PATH
            fvm_default_bin = self.fvm_home / "default" / "bin"
            if fvm_default_bin.exists():
                self.dep_manager.add_to_path(str(fvm_default_bin), self.config.get_shell_profile())
            
            # Also add pub cache bin to PATH if not already there
            pub_cache_bin = self.config.pub_cache_bin_dir
            self.dep_manager.add_to_path(str(pub_cache_bin), self.config.get_shell_profile())
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: PATH setup failed: {e}[/yellow]")
            return False
    
    def build_project(self, project_path: Path, platforms: Optional[List[str]] = None) -> bool:
        """Build Flutter project for specified platforms using FVM."""
        if platforms is None:
            platforms = self.config.platforms
        
        if not self.is_flutter_installed():
            console.print("[red]Flutter is not installed[/red]")
            return False
        
        success = True
        
        for platform in platforms:
            console.print(f"[blue]Building for {platform}...[/blue]")
            
            try:
                if platform == "web":
                    # Try profile build first, then regular build
                    result = self.executor.run_command(
                        "fvm flutter build web --dart-define=FLUTTER_WEB_USE_SKIA=true --web-renderer=canvaskit --profile",
                        cwd=project_path,
                        timeout=120,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        console.print("[yellow]Profile build failed, trying regular build...[/yellow]")
                        result = self.executor.run_command(
                            "fvm flutter build web",
                            cwd=project_path,
                            timeout=120,
                            check=False
                        )
                
                elif platform == "android":
                    result = self.executor.run_command(
                        "fvm flutter build apk",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                elif platform == "linux":
                    result = self.executor.run_command(
                        "fvm flutter build linux",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                elif platform == "macos":
                    result = self.executor.run_command(
                        "fvm flutter build macos",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                elif platform == "windows":
                    result = self.executor.run_command(
                        "fvm flutter build windows",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                elif platform == "ios":
                    result = self.executor.run_command(
                        "fvm flutter build ios --no-codesign",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                else:
                    console.print(f"[yellow]Unsupported platform: {platform}[/yellow]")
                    continue
                
                if result.returncode == 0:
                    console.print(f"[green]Build for {platform} completed successfully[/green]")
                else:
                    console.print(f"[yellow]Build for {platform} failed (expected for initial setup)[/yellow]")
                    success = False
                
            except Exception as e:
                console.print(f"[red]Build for {platform} failed: {e}[/red]")
                success = False
        
        return success
    
    def switch_version(self, version: str) -> bool:
        """Switch to a different Flutter version."""
        if not self.is_fvm_installed():
            console.print("[red]FVM is not installed[/red]")
            return False
        
        try:
            console.print(f"[blue]Switching to Flutter {version}...[/blue]")
            
            # Check if version is installed
            result = self.executor.run_command(
                "fvm list",
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0 and version not in result.stdout:
                console.print(f"[blue]Flutter {version} not installed, installing now...[/blue]")
                install_result = self.executor.run_command(
                    f"fvm install {version}",
                    timeout=600,
                    check=False
                )
                
                if install_result.returncode != 0:
                    console.print(f"[red]Failed to install Flutter {version}[/red]")
                    return False
            
            # Switch to version
            result = self.executor.run_command(
                f"fvm global {version}",
                check=False
            )
            
            if result.returncode == 0:
                console.print(f"[green]Switched to Flutter {version}[/green]")
                self.config.flutter_version = version
                return True
            else:
                console.print(f"[red]Failed to switch to Flutter {version}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Version switch failed: {e}[/red]")
            return False