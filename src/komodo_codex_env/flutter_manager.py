"""Flutter SDK installation and management."""

import tarfile
import zipfile
from pathlib import Path
from typing import Optional
from packaging.version import Version
from rich.console import Console
from rich.progress import Progress, DownloadColumn, BarColumn, TextColumn

import requests

from .config import EnvironmentConfig
from .executor import CommandExecutor
from .dependency_manager import DependencyManager

console = Console()


class FlutterManager:
    """Manages Flutter SDK installation and configuration."""
    
    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor, dep_manager: DependencyManager):
        self.config = config
        self.executor = executor
        self.dep_manager = dep_manager
        
    def is_flutter_installed(self) -> bool:
        """Check if Flutter is already installed."""
        flutter_bin = self.config.flutter_bin_dir / "flutter"
        return flutter_bin.exists() and flutter_bin.is_file()
    
    def get_installed_version(self) -> Optional[Version]:
        """Get the currently installed Flutter version."""
        if not self.is_flutter_installed():
            return None
        
        try:
            version_file = self.config.flutter_dir / "version"
            if version_file.exists():
                version_str = version_file.read_text().strip()
                return Version(version_str)
            
            # Fallback to flutter --version command
            result = self.executor.run_command(
                "flutter --version --machine",
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                import json
                version_info = json.loads(result.stdout)
                return Version(version_info.get("frameworkVersion", "0.0.0"))
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not determine Flutter version: {e}[/yellow]")
        
        return None
    
    def install_flutter(self) -> bool:
        """Install Flutter SDK."""
        if self.is_flutter_installed():
            console.print("[green]Flutter is already installed[/green]")
            return True
        
        console.print(f"[blue]Installing Flutter {self.config.flutter_version}...[/blue]")
        
        # Check disk space
        if not self.dep_manager.check_disk_space(1.5):  # Flutter needs ~1.5GB
            console.print("[red]Insufficient disk space for Flutter installation[/red]")
            return False
        
        # Create flutter directory
        self.config.flutter_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.flutter_install_method == "precompiled":
            return self._install_precompiled()
        else:
            return self._install_from_git()
    
    def _install_precompiled(self) -> bool:
        """Install Flutter from pre-compiled binaries."""
        try:
            # Determine the correct archive URL
            system_info = self.dep_manager.get_system_info()
            os_name = system_info.get("os", "").lower()
            arch = system_info.get("arch", "").lower()
            
            if "linux" in os_name:
                platform = "linux"
                extension = "tar.xz"
            elif "darwin" in os_name:
                platform = "macos"
                extension = "zip"
            else:
                console.print(f"[yellow]Unsupported OS for precompiled install: {os_name}[/yellow]")
                console.print("[blue]Falling back to Git installation...[/blue]")
                return self._install_from_git()
            
            # Format version for download URL
            version = self.config.get_flutter_version()
            version_str = f"{version.major}.{version.minor}.{version.micro}"
            
            archive_name = f"flutter_{platform}_{version_str}-stable.{extension}"
            download_url = f"https://storage.googleapis.com/flutter_infra_release/releases/stable/{platform}/{archive_name}"
            
            console.print(f"[blue]Downloading Flutter from: {download_url}[/blue]")
            
            # Download with progress bar
            archive_path = self.config.home_dir / archive_name
            if not self._download_file(download_url, archive_path):
                console.print("[yellow]Download failed, falling back to Git installation...[/yellow]")
                return self._install_from_git()
            
            # Extract archive
            console.print("[blue]Extracting Flutter SDK...[/blue]")
            if not self._extract_archive(archive_path, self.config.home_dir):
                console.print("[red]Failed to extract Flutter archive[/red]")
                archive_path.unlink(missing_ok=True)
                return False
            
            # Clean up archive
            archive_path.unlink(missing_ok=True)
            
            # Verify installation
            if not self.is_flutter_installed():
                console.print("[red]Flutter installation verification failed[/red]")
                return False
            
            console.print("[green]Flutter pre-compiled installation completed successfully![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Pre-compiled installation failed: {e}[/red]")
            console.print("[blue]Falling back to Git installation...[/blue]")
            return self._install_from_git()
    
    def _install_from_git(self) -> bool:
        """Install Flutter from Git repository."""
        try:
            console.print("[blue]Installing Flutter from Git repository...[/blue]")
            
            # Remove any existing flutter directory
            if self.config.flutter_dir.exists():
                import shutil
                shutil.rmtree(self.config.flutter_dir)
            
            # Clone Flutter repository
            clone_cmd = f"git clone --depth 1 --branch {self.config.flutter_version} https://github.com/flutter/flutter.git {self.config.flutter_dir}"
            
            result = self.executor.run_command(
                clone_cmd,
                cwd=self.config.home_dir,
                timeout=300,  # 5 minutes timeout
                check=False
            )
            
            if result.returncode != 0:
                console.print("[red]Failed to clone Flutter repository[/red]")
                return False
            
            # Configure Git for Flutter directory
            self._configure_flutter_git()
            
            console.print("[green]Flutter Git installation completed successfully![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Git installation failed: {e}[/red]")
            return False
    
    def _download_file(self, url: str, destination: Path) -> bool:
        """Download a file with progress bar."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TextColumn("[bold green]{task.fields[speed]}", justify="right"),
            ) as progress:
                
                task = progress.add_task(
                    "download",
                    filename=destination.name,
                    total=total_size,
                    speed="0 MB/s"
                )
                
                with destination.open("wb") as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task, advance=len(chunk))
            
            return True
            
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            return False
    
    def _extract_archive(self, archive_path: Path, destination: Path) -> bool:
        """Extract a tar.xz or zip archive."""
        try:
            if archive_path.suffix == ".xz":
                with tarfile.open(archive_path, "r:xz") as tar:
                    tar.extractall(destination)
            elif archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_file:
                    zip_file.extractall(destination)
            else:
                console.print(f"[red]Unsupported archive format: {archive_path.suffix}[/red]")
                return False
            
            return True
            
        except Exception as e:
            console.print(f"[red]Archive extraction failed: {e}[/red]")
            return False
    
    def _configure_flutter_git(self) -> bool:
        """Configure Git settings for Flutter directory."""
        try:
            # Fix ownership issues
            import subprocess
            import getpass
            
            username = getpass.getuser()
            subprocess.run(
                ["sudo", "chown", "-R", f"{username}:{username}", str(self.config.flutter_dir)],
                check=False
            )
            
            # Configure Git to trust this directory
            self.executor.run_command(
                f"git config --global --add safe.directory {self.config.flutter_dir}",
                check=False
            )
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Git configuration failed: {e}[/yellow]")
            return False
    
    def configure_flutter(self) -> bool:
        """Configure Flutter after installation."""
        if not self.is_flutter_installed():
            console.print("[red]Flutter is not installed[/red]")
            return False
        
        try:
            console.print("[blue]Configuring Flutter...[/blue]")
            
            # Disable analytics
            self.executor.run_command("flutter config --no-analytics")
            
            # Pre-cache for web platform only
            console.print("[blue]Pre-caching Flutter assets for web...[/blue]")
            self.executor.run_command(
                "flutter precache --web --no-android --no-ios --no-fuchsia --no-linux --no-macos --no-windows",
                timeout=300
            )
            
            # Run Flutter doctor
            console.print("[blue]Running Flutter doctor...[/blue]")
            result = self.executor.run_command(
                "flutter doctor --no-analytics",
                timeout=60,
                check=False
            )
            
            if result.returncode != 0:
                console.print("[yellow]Flutter doctor completed with warnings[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Flutter configuration failed: {e}[/red]")
            return False
    
    def build_project(self, project_path: Path, platforms: Optional[list] = None) -> bool:
        """Build Flutter project for specified platforms."""
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
                        "flutter build web --dart-define=FLUTTER_WEB_USE_SKIA=true --web-renderer=canvaskit --profile",
                        cwd=project_path,
                        timeout=120,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        console.print("[yellow]Profile build failed, trying regular build...[/yellow]")
                        result = self.executor.run_command(
                            "flutter build web",
                            cwd=project_path,
                            timeout=120,
                            check=False
                        )
                
                elif platform == "android":
                    result = self.executor.run_command(
                        "flutter build apk",
                        cwd=project_path,
                        timeout=300,
                        check=False
                    )
                
                elif platform == "linux":
                    result = self.executor.run_command(
                        "flutter build linux",
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
                    console.print(f"[yellow]Build for {platform} failed (expected for setup)[/yellow]")
                    success = False
                
            except Exception as e:
                console.print(f"[red]Build for {platform} failed: {e}[/red]")
                success = False
        
        return success
