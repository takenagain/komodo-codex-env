"""System dependency management and installation."""

import shutil
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console

from .executor import CommandExecutor

console = Console()


class DependencyManager:
    """Manages system dependencies and their installation."""
    
    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self._package_managers = {
            "apt": self._handle_apt,
            "brew": self._handle_brew,
            "pacman": self._handle_pacman,
        }
        self._platform_packages = self._get_platform_packages()
    
    def _get_platform_packages(self) -> Dict[str, Dict[str, str]]:
        """Get platform-specific package names."""
        return {
            "apt": {
                "curl": "curl",
                "git": "git",
                "unzip": "unzip",
                "xz-utils": "xz-utils",
                "zip": "zip",
                "libglu1-mesa": "libglu1-mesa",
                "build-essential": "build-essential",
                "dart": "dart",
            },
            "brew": {
                "curl": "curl",
                "git": "git", 
                "unzip": "unzip",
                "xz-utils": "xz",  # Different name on macOS
                "zip": "zip",
                "libglu1-mesa": "",  # Not needed on macOS
                "build-essential": "",  # Not needed on macOS (Xcode tools)
                "dart": "dart",
            },
            "pacman": {
                "curl": "curl",
                "git": "git",
                "unzip": "unzip", 
                "xz-utils": "xz",
                "zip": "zip",
                "libglu1-mesa": "glu",
                "build-essential": "base-devel",
                "dart": "dart",
            }
        }
    
    def detect_package_manager(self) -> Optional[str]:
        """Detect the available package manager."""
        for pm in self._package_managers.keys():
            if self.executor.check_command_exists(pm):
                return pm
        return None
    
    def check_dependencies(self, dependencies: List[str]) -> Dict[str, bool]:
        """Check which dependencies are installed."""
        results = {}
        pm = self.detect_package_manager()
        
        for dep in dependencies:
            # Handle special cases for commands vs packages
            if dep in ["curl", "git", "unzip", "zip"]:
                # These are typically commands
                results[dep] = self._is_command_available(dep)
            elif dep == "xz-utils":
                # Check for xz command instead of package
                results[dep] = self._is_command_available("xz")
            elif dep == "libglu1-mesa":
                # Platform-specific library check
                if pm == "brew":
                    results[dep] = True  # Not needed on macOS
                else:
                    results[dep] = self._is_package_installed(dep)
            else:
                if self._is_command_available(dep):
                    results[dep] = True
                elif self._is_package_installed(dep):
                    results[dep] = True
                else:
                    results[dep] = False
        
        return results
    
    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        return shutil.which(command) is not None
    
    def _is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using the system package manager."""
        pm = self.detect_package_manager()
        
        if pm == "apt":
            try:
                result = self.executor.run_command(
                    f"dpkg -l | grep -q ' {package} '",
                    check=False,
                    capture_output=True
                )
                return result.returncode == 0
            except Exception:
                return False
        
        elif pm == "brew":
            try:
                result = self.executor.run_command(
                    f"brew list {package}",
                    check=False,
                    capture_output=True
                )
                return result.returncode == 0
            except Exception:
                return False
        
        elif pm == "pacman":
            try:
                result = self.executor.run_command(
                    f"pacman -Q {package}",
                    check=False,
                    capture_output=True
                )
                return result.returncode == 0
            except Exception:
                return False
        
        return False
    
    def install_dependencies(self, dependencies: List[str]) -> bool:
        """Install missing dependencies."""
        dependency_status = self.check_dependencies(dependencies)
        missing_deps = [dep for dep, installed in dependency_status.items() if not installed]
        
        if not missing_deps:
            console.print("[green]All required dependencies are already installed.[/green]")
            return True
        
        console.print(f"[blue]Installing missing dependencies: {', '.join(missing_deps)}[/blue]")
        
        pm = self.detect_package_manager()
        if not pm:
            console.print("[red]No supported package manager found[/red]")
            return False
        
        # Map generic dependency names to platform-specific package names
        platform_deps = []
        for dep in missing_deps:
            if pm in self._platform_packages and dep in self._platform_packages[pm]:
                platform_package = self._platform_packages[pm][dep]
                if platform_package:  # Skip empty packages (not needed on platform)
                    platform_deps.append(platform_package)
            else:
                platform_deps.append(dep)  # Use as-is if no mapping
        
        if not platform_deps:
            console.print("[green]No packages need to be installed on this platform.[/green]")
            return True
        
        return self._package_managers[pm](platform_deps)
    
    def _handle_apt(self, packages: List[str]) -> bool:
        """Handle APT package installation."""
        try:
            # Update package list first
            console.print("[blue]Updating package list...[/blue]")
            self.executor.run_command("sudo apt-get update -y")
            
            # Install packages
            packages_str = " ".join(packages)
            self.executor.run_command(f"sudo apt-get install -y {packages_str}")
            
            return True
            
        except Exception as e:
            console.print(f"[red]APT installation failed: {e}[/red]")
            return False
    
    def _handle_brew(self, packages: List[str]) -> bool:
        """Handle Homebrew package installation."""
        try:
            # Filter out packages that might not exist or are not needed
            valid_packages = []
            for package in packages:
                if package and package not in ["", "libglu1-mesa"]:
                    valid_packages.append(package)
            
            if not valid_packages:
                console.print("[green]No Homebrew packages need to be installed.[/green]")
                return True
            
            for package in valid_packages:
                console.print(f"[blue]Installing {package} with Homebrew...[/blue]")
                result = self.executor.run_command(f"brew install {package}", check=False)
                if result.returncode != 0:
                    console.print(f"[yellow]Warning: Could not install {package} via Homebrew[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Homebrew installation failed: {e}[/red]")
            return False
    
    def _handle_pacman(self, packages: List[str]) -> bool:
        """Handle Pacman package installation."""
        try:
            # Update package database first
            console.print("[blue]Updating package database...[/blue]")
            self.executor.run_command("sudo pacman -Sy")
            
            # Install packages
            packages_str = " ".join(packages)
            self.executor.run_command(f"sudo pacman -S --noconfirm {packages_str}")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Pacman installation failed: {e}[/red]")
            return False
    
    def check_disk_space(self, required_gb: float, path: Optional[Path] = None) -> bool:
        """Check if there's enough disk space available."""
        if path is None:
            path = Path.home()
        
        try:
            result = self.executor.run_command(
                f"df -k {path}",
                capture_output=True
            )
            
            # Parse df output
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                # Get available space in KB
                available_kb = int(lines[1].split()[3])
                available_gb = available_kb / (1024 * 1024)
                
                console.print(f"[blue]Available space: {available_gb:.1f}GB, Required: {required_gb}GB[/blue]")
                
                return available_gb >= required_gb
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not check disk space: {e}[/yellow]")
            # Assume we have enough space if check fails
            return True
        
        return False
    
    def get_system_info(self) -> Dict[str, str]:
        """Get basic system information."""
        info = {}
        
        # OS information
        try:
            result = self.executor.run_command("uname -s", capture_output=True, check=False)
            if result.returncode == 0:
                info["os"] = result.stdout.strip()
        except Exception:
            pass
        
        # Architecture
        try:
            result = self.executor.run_command("uname -m", capture_output=True, check=False)
            if result.returncode == 0:
                info["arch"] = result.stdout.strip()
        except Exception:
            pass
        
        # Distribution (Linux)
        if info.get("os") == "Linux":
            try:
                # Try lsb_release first
                result = self.executor.run_command(
                    "lsb_release -d -s", capture_output=True, check=False
                )
                if result.returncode == 0:
                    info["distro"] = result.stdout.strip().strip('"')
                else:
                    # Try /etc/os-release
                    result = self.executor.run_command(
                        "cat /etc/os-release | grep PRETTY_NAME",
                        capture_output=True, check=False
                    )
                    if result.returncode == 0:
                        line = result.stdout.strip()
                        if "=" in line:
                            info["distro"] = line.split("=", 1)[1].strip('"')
            except Exception:
                pass
        
        return info
    
    def setup_environment_variables(self, env_vars: Dict[str, str], profile_path: Path) -> bool:
        """Add environment variables to shell profile."""
        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing profile content
            existing_content = ""
            if profile_path.exists():
                existing_content = profile_path.read_text()
            
            # Add new environment variables
            new_lines = []
            for var, value in env_vars.items():
                export_line = f'export {var}="{value}"'
                
                # Check if variable is already set
                if f"export {var}=" not in existing_content and f"{var}=" not in existing_content:
                    new_lines.append(export_line)
                    console.print(f"[blue]Adding to profile: {export_line}[/blue]")
            
            if new_lines:
                with profile_path.open("a") as f:
                    f.write("\n# Added by Komodo Codex Environment Setup\n")
                    for line in new_lines:
                        f.write(f"{line}\n")
                
                console.print(f"[green]Updated {profile_path}[/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to update environment variables: {e}[/red]")
            return False
    
    def add_environment_variable(self, var_name: str, var_value: str, profile_path: Path) -> bool:
        """Add an environment variable to the shell profile."""
        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing profile content
            existing_content = ""
            if profile_path.exists():
                existing_content = profile_path.read_text()
            
            # Check if variable is already set
            export_line = f'export {var_name}="{var_value}"'
            var_pattern = f'export {var_name}='
            
            if var_pattern in existing_content:
                console.print(f"[yellow]{var_name} already configured[/yellow]")
                return True
            
            # Add environment variable
            with profile_path.open("a") as f:
                f.write(f"\n# Added by Komodo Codex Environment Setup\n")
                f.write(f"{export_line}\n")
            
            console.print(f"[green]Added {var_name} environment variable[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to add environment variable: {e}[/red]")
            return False

    def add_to_path(self, path_entry: str, profile_path: Path) -> bool:
        """Add a directory to PATH in the shell profile."""
        try:
            # Normalize path
            path_entry = str(Path(path_entry).resolve())
            
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing profile content
            existing_content = ""
            if profile_path.exists():
                existing_content = profile_path.read_text()
            
            # Check if path is already in profile
            if path_entry in existing_content:
                console.print(f"[yellow]{path_entry} already in PATH configuration[/yellow]")
                return True
            
            # Add to PATH
            export_line = f'export PATH="$PATH:{path_entry}"'
            
            with profile_path.open("a") as f:
                f.write(f"\n# Added by Komodo Codex Environment Setup\n")
                f.write(f"{export_line}\n")
            
            console.print(f"[green]Added {path_entry} to PATH[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to add to PATH: {e}[/red]")
            return False
    
    def _handle_pacman(self, packages: List[str]) -> bool:
        """Handle Pacman package installation."""
        try:
            # Update package database first
            console.print("[blue]Updating package database...[/blue]")
            self.executor.run_command("sudo pacman -Sy")
            
            # Install packages
            packages_str = " ".join(packages)
            self.executor.run_command(f"sudo pacman -S --noconfirm {packages_str}")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Pacman installation failed: {e}[/red]")
            return False
    
    def check_disk_space(self, required_gb: float, path: Optional[Path] = None) -> bool:
        """Check if there's enough disk space available."""
        if path is None:
            path = Path.home()
        
        try:
            result = self.executor.run_command(
                f"df -k {path}",
                capture_output=True
            )
            
            # Parse df output
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                # Get available space in KB
                available_kb = int(lines[1].split()[3])
                available_gb = available_kb / (1024 * 1024)
                
                console.print(f"[blue]Available space: {available_gb:.1f}GB, Required: {required_gb}GB[/blue]")
                
                return available_gb >= required_gb
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not check disk space: {e}[/yellow]")
            # Assume we have enough space if check fails
            return True
        
        return False
    
    def get_system_info(self) -> Dict[str, str]:
        """Get basic system information."""
        info = {}
        
        # OS information
        try:
            result = self.executor.run_command("uname -s", capture_output=True, check=False)
            if result.returncode == 0:
                info["os"] = result.stdout.strip()
        except Exception:
            pass
        
        # Architecture
        try:
            result = self.executor.run_command("uname -m", capture_output=True, check=False)
            if result.returncode == 0:
                info["arch"] = result.stdout.strip()
        except Exception:
            pass
        
        # Distribution (Linux)
        if info.get("os") == "Linux":
            try:
                # Try lsb_release first
                result = self.executor.run_command(
                    "lsb_release -d -s", capture_output=True, check=False
                )
                if result.returncode == 0:
                    info["distro"] = result.stdout.strip().strip('"')
                else:
                    # Try /etc/os-release
                    result = self.executor.run_command(
                        "cat /etc/os-release | grep PRETTY_NAME",
                        capture_output=True, check=False
                    )
                    if result.returncode == 0:
                        line = result.stdout.strip()
                        if "=" in line:
                            info["distro"] = line.split("=", 1)[1].strip('"')
            except Exception:
                pass
        
        return info
    
    def setup_environment_variables(self, env_vars: Dict[str, str], profile_path: Path) -> bool:
        """Add environment variables to shell profile."""
        try:
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing profile content
            existing_content = ""
            if profile_path.exists():
                existing_content = profile_path.read_text()
            
            # Add new environment variables
            new_lines = []
            for var, value in env_vars.items():
                export_line = f'export {var}="{value}"'
                
                # Check if variable is already set
                if f"export {var}=" not in existing_content and f"{var}=" not in existing_content:
                    new_lines.append(export_line)
                    console.print(f"[blue]Adding to profile: {export_line}[/blue]")
            
            if new_lines:
                with profile_path.open("a") as f:
                    f.write("\n# Added by Komodo Codex Environment Setup\n")
                    for line in new_lines:
                        f.write(f"{line}\n")
                
                console.print(f"[green]Updated {profile_path}[/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to update environment variables: {e}[/red]")
            return False
    
    def add_to_path(self, path_entry: str, profile_path: Path) -> bool:
        """Add a directory to PATH in the shell profile."""
        try:
            # Normalize path
            path_entry = str(Path(path_entry).resolve())
            
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing profile content
            existing_content = ""
            if profile_path.exists():
                existing_content = profile_path.read_text()
            
            # Check if path is already in profile
            if path_entry in existing_content:
                console.print(f"[yellow]{path_entry} already in PATH configuration[/yellow]")
                return True
            
            # Add to PATH
            export_line = f'export PATH="$PATH:{path_entry}"'
            
            with profile_path.open("a") as f:
                f.write(f"\n# Added by Komodo Codex Environment Setup\n")
                f.write(f"{export_line}\n")
            
            console.print(f"[green]Added {path_entry} to PATH[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to add to PATH: {e}[/red]")
            return False
