"""Git operations and repository management."""

import re
from pathlib import Path
from typing import Optional, List
from rich.console import Console

from .executor import CommandExecutor

console = Console()


class GitManager:
    """Manages Git operations for the project."""
    
    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self._repo_info = None
    
    def is_git_repo(self, path: Optional[Path] = None) -> bool:
        """Check if the current directory is a Git repository."""
        if path is None:
            path = Path.cwd()
        
        try:
            result = self.executor.run_command(
                "git rev-parse --is-inside-work-tree",
                cwd=path,
                check=False,
                capture_output=True
            )
            
            if result.returncode != 0:
                return False
            
            # Check if this directory (not a parent) is the git root
            git_root_result = self.executor.run_command(
                "git rev-parse --show-toplevel",
                cwd=path,
                check=False,
                capture_output=True
            )
            
            if git_root_result.returncode == 0:
                git_root = Path(git_root_result.stdout.strip())
                return git_root.resolve() == path.resolve()
            
            return False
            
        except Exception as e:
            console.print(f"[yellow]Warning: Git check failed: {e}[/yellow]")
            return False
    
    def get_repo_name(self, path: Optional[Path] = None) -> Optional[str]:
        """Get the name of the Git repository."""
        if not self.is_git_repo(path):
            return None
        
        try:
            if path is None:
                path = Path.cwd()
            
            result = self.executor.run_command(
                "git rev-parse --show-toplevel",
                cwd=path,
                check=False,
                capture_output=True
            )
            
            if result.returncode == 0:
                repo_path = Path(result.stdout.strip())
                return repo_path.name
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not get repo name: {e}[/yellow]")
        
        return None
    
    def get_remote_url(self, remote: str = "origin", path: Optional[Path] = None) -> Optional[str]:
        """Get the remote URL for the repository."""
        if not self.is_git_repo(path):
            return None
        
        try:
            result = self.executor.run_command(
                f"git remote get-url {remote}",
                cwd=path,
                check=False,
                capture_output=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not get remote URL: {e}[/yellow]")
        
        return None
    
    def add_remote(self, name: str, url: str, path: Optional[Path] = None) -> bool:
        """Add a remote to the repository."""
        try:
            # Check if remote already exists
            existing_url = self.get_remote_url(name, path)
            
            if existing_url:
                if existing_url != url:
                    console.print(f"[yellow]Updating remote {name} URL[/yellow]")
                    self.executor.run_command(
                        f"git remote set-url {name} {url}",
                        cwd=path
                    )
                return True
            else:
                console.print(f"[blue]Adding remote {name}[/blue]")
                self.executor.run_command(
                    f"git remote add {name} {url}",
                    cwd=path
                )
                return True
                
        except Exception as e:
            console.print(f"[red]Failed to add remote {name}: {e}[/red]")
            return False
    
    def fetch_all_branches(self, timeout: int = 120, path: Optional[Path] = None) -> bool:
        """Fetch all remote branches."""
        if not self.is_git_repo(path):
            console.print("[yellow]Not in a Git repository, skipping fetch[/yellow]")
            return False
        
        try:
            console.print("[blue]Fetching all remote branches...[/blue]")
            result = self.executor.run_command(
                "git fetch --all",
                cwd=path,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                console.print("[yellow]Git fetch failed or timed out[/yellow]")
                return False
            
            return True
            
        except Exception as e:
            console.print(f"[red]Git fetch operation failed: {e}[/red]")
            return False
    
    def checkout_branch(self, branch: str, create: bool = False, path: Optional[Path] = None) -> bool:
        """Checkout a branch, optionally creating it."""
        try:
            if create:
                # Check if branch exists remotely
                remote_branches_result = self.executor.run_command(
                    "git branch -r",
                    cwd=path,
                    check=False,
                    capture_output=True
                )
                
                if remote_branches_result.returncode == 0:
                    remote_branches = remote_branches_result.stdout
                    if f"origin/{branch}" in remote_branches:
                        command = f"git checkout -b {branch} origin/{branch}"
                    else:
                        command = f"git checkout -b {branch}"
                else:
                    command = f"git checkout -b {branch}"
            else:
                command = f"git checkout {branch}"
            
            result = self.executor.run_command(
                command,
                cwd=path,
                check=False
            )
            
            return result.returncode == 0
            
        except Exception as e:
            console.print(f"[red]Failed to checkout branch {branch}: {e}[/red]")
            return False
    
    def get_current_branch(self, path: Optional[Path] = None) -> Optional[str]:
        """Get the current branch name."""
        try:
            result = self.executor.run_command(
                "git branch --show-current",
                cwd=path,
                check=False,
                capture_output=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception as e:
            console.print(f"[yellow]Could not get current branch: {e}[/yellow]")
        
        return None
    
    def update_git_exclude(self, patterns: List[str], path: Optional[Path] = None) -> bool:
        """Update .git/info/exclude file with patterns."""
        if not self.is_git_repo(path):
            return False
        
        try:
            if path is None:
                path = Path.cwd()
            
            exclude_file = path / ".git" / "info" / "exclude"
            exclude_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing patterns
            existing_patterns = set()
            if exclude_file.exists():
                existing_patterns = set(exclude_file.read_text().splitlines())
            
            # Add new patterns
            new_patterns = []
            for pattern in patterns:
                if pattern not in existing_patterns:
                    new_patterns.append(pattern)
                    existing_patterns.add(pattern)
            
            if new_patterns:
                console.print(f"[blue]Adding {len(new_patterns)} patterns to .git/info/exclude[/blue]")
                with exclude_file.open("a") as f:
                    for pattern in new_patterns:
                        f.write(f"{pattern}\n")
            
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not update git exclude file: {e}[/yellow]")
            return False
    
    def configure_safe_directory(self, path: Path) -> bool:
        """Configure Git to trust a directory (for ownership issues)."""
        try:
            self.executor.run_command(
                f"git config --global --add safe.directory {path}",
                check=False
            )
            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Could not configure safe directory: {e}[/yellow]")
            return False
