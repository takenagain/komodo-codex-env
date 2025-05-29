"""Documentation fetching and management."""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from rich.console import Console
import urllib3

import requests

from .config import EnvironmentConfig
from .executor import CommandExecutor

# Disable SSL warnings when verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class DocumentationManager:
    """Manages fetching and organizing documentation files."""

    def __init__(self, config: EnvironmentConfig, executor: CommandExecutor):
        self.config = config
        self.executor = executor

        # Documentation sources
        self.doc_sources = {
            "agents": self.config.agents_gist_url,
            "bloc_conventions": "https://raw.githubusercontent.com/felangel/bloc/refs/heads/master/docs/src/content/docs/naming-conventions.mdx",
            "bloc_modeling": "https://raw.githubusercontent.com/felangel/bloc/refs/heads/master/docs/src/content/docs/modeling-state.mdx",
            "bloc_testing": "https://raw.githubusercontent.com/felangel/bloc/refs/heads/master/docs/src/content/docs/testing.mdx",
            "bloc_concepts": "https://raw.githubusercontent.com/felangel/bloc/refs/heads/master/docs/src/content/docs/flutter-bloc-concepts.mdx",
            "commit_conventions": "https://raw.githubusercontent.com/conventional-commits/conventionalcommits.org/refs/heads/master/content/v1.0.0/index.md",
            "kdf_api": self.config.kdf_api_docs_url
        }

    async def fetch_all_documentation(self) -> Dict[str, str]:
        """Fetch all documentation files concurrently."""
        console.print("[blue]Fetching documentation files...[/blue]")

        tasks = []
        task_names = []
        for name, url in self.doc_sources.items():
            # Skip KDF API docs if not requested
            if name == "kdf_api" and not self.config.should_fetch_kdf_api_docs:
                continue

            # Skip agents docs if not requested
            if name == "agents" and not self.config.should_fetch_agents_docs:
                continue

            task = asyncio.create_task(self._fetch_document(name, url))
            tasks.append(task)
            task_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        documents = {}
        for i, result in enumerate(results):
            task_name = task_names[i]

            if isinstance(result, Exception):
                console.print(f"[red]Failed to fetch {task_name}: {result}[/red]")
            elif result:
                name, content = result
                documents[name] = content
                console.print(f"[green]Fetched {name} ({len(content)} characters)[/green]")

        return documents

    async def _fetch_document(self, name: str, url: str) -> Optional[tuple]:
        """Fetch a single document with SSL fallback handling."""
        # Try with SSL verification first, then without if it fails
        ssl_configs = [
            {"verify": True, "timeout": 10},
            {"verify": False, "timeout": 15}
        ]

        for i, config in enumerate(ssl_configs):
            try:
                if i == 1:
                    console.print(f"[yellow]Retrying {name} without SSL verification...[/yellow]")

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, **config)
                )
                response.raise_for_status()

                content = response.text
                if content.strip():
                    if i == 1:
                        console.print(f"[yellow]Successfully fetched {name} without SSL verification[/yellow]")
                    return (name, content)
                else:
                    console.print(f"[yellow]Warning: Empty content for {name}[/yellow]")
                    return None

            except Exception as e:
                if i == 0:
                    # First attempt failed, try without SSL
                    continue
                else:
                    # Both attempts failed
                    console.print(f"[red]Failed to fetch {name} from {url}: {e}[/red]")
                    return None

        return None

    def save_documentation(self, documents: Dict[str, str], target_dir: Path) -> bool:
        """Save documentation files to the target directory."""
        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            for name, content in documents.items():
                if name == "agents":
                    file_path = self._get_agents_file_path(target_dir)
                elif name == "kdf_api":
                    file_path = target_dir / "KDF_API_DOCUMENTATION.md"
                else:
                    # Save other docs to a subdirectory
                    docs_dir = target_dir / "docs"
                    docs_dir.mkdir(exist_ok=True)
                    file_path = docs_dir / f"{name}.md"

                file_path.write_text(content, encoding="utf-8")
                console.print(f"[green]Saved {name} to {file_path}[/green]")

            return True

        except Exception as e:
            console.print(f"[red]Failed to save documentation: {e}[/red]")
            return False

    def _get_agents_file_path(self, target_dir: Path) -> Path:
        """Get the appropriate path for the AGENTS.md file."""
        base_path = target_dir / "AGENTS.md"

        if not base_path.exists():
            return base_path

        # Find the highest version number
        max_num = 0
        for existing_file in target_dir.glob("AGENTS_*.md"):
            try:
                num_str = existing_file.stem.split("_")[1]
                num = int(num_str)
                max_num = max(max_num, num)
            except (IndexError, ValueError):
                continue

        # Create new versioned file
        next_num = max_num + 1
        versioned_path = target_dir / f"AGENTS_{next_num}.md"

        console.print(f"[yellow]AGENTS.md exists, saving to {versioned_path.name}[/yellow]")
        return versioned_path

    def create_combined_documentation(self, documents: Dict[str, str], target_dir: Path) -> bool:
        """Create a combined documentation file with all fetched content."""
        try:
            if "agents" not in documents:
                console.print("[yellow]No AGENTS documentation to combine with[/yellow]")
                return False

            agents_content = documents["agents"]

            # Add Bloc conventions
            bloc_docs = []
            for key in ["bloc_conventions", "bloc_modeling", "bloc_testing", "bloc_concepts"]:
                if key in documents:
                    bloc_docs.append(documents[key])

            if bloc_docs:
                agents_content += "\n\n# Bloc Framework Documentation\n\n"
                agents_content += "\n\n".join(bloc_docs)

            # Add commit conventions
            if "commit_conventions" in documents:
                agents_content += "\n\n# Commit Conventions\n\n"
                agents_content += documents["commit_conventions"]

            # Save combined file
            combined_path = self._get_agents_file_path(target_dir)
            combined_path.write_text(agents_content, encoding="utf-8")

            console.print(f"[green]Created combined documentation: {combined_path}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to create combined documentation: {e}[/red]")
            return False

    def update_git_exclude(self, target_dir: Path, patterns: Optional[List[str]] = None) -> bool:
        """Update git exclude file to ignore downloaded documentation."""
        if patterns is None:
            patterns = [
                "AGENTS.md",
                "AGENTS_*.md",
                "KDF_API_DOCUMENTATION.md",
                "docs/bloc_*.md",
                "docs/commit_*.md"
            ]

        try:
            git_info_dir = target_dir / ".git" / "info"
            if not git_info_dir.exists():
                console.print("[yellow]Not in a git repository, skipping git exclude update[/yellow]")
                return False

            exclude_file = git_info_dir / "exclude"

            # Read existing content
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
                with exclude_file.open("a") as f:
                    f.write("\n# Documentation files added by Komodo Codex Environment Setup\n")
                    for pattern in new_patterns:
                        f.write(f"{pattern}\n")

                console.print(f"[green]Added {len(new_patterns)} patterns to .git/info/exclude[/green]")

            return True

        except Exception as e:
            console.print(f"[yellow]Warning: Could not update git exclude: {e}[/yellow]")
            return False

    def check_for_script_updates(self) -> Optional[str]:
        """Check if there's a newer version of the script available."""
        # Try with SSL verification first, then without if it fails
        ssl_configs = [
            {"verify": True, "timeout": 10},
            {"verify": False, "timeout": 10}
        ]

        for i, config in enumerate(ssl_configs):
            try:
                if i == 1:
                    console.print("[yellow]Retrying script update check without SSL verification...[/yellow]")

                response = requests.get(self.config.script_gist_url, **config)
                response.raise_for_status()

                script_content = response.text

                # Extract version from script content
                import re
                version_match = re.search(r'SCRIPT_VERSION="([^"]+)"', script_content)

                if version_match:
                    latest_version = version_match.group(1)

                    if latest_version != self.config.script_version:
                        console.print(f"[yellow]Script update available: {latest_version} (current: {self.config.script_version})[/yellow]")
                        return latest_version
                    else:
                        console.print(f"[green]Script is up to date: {self.config.script_version}[/green]")

                return None

            except Exception as e:
                if i == 0:
                    # First attempt failed, try without SSL
                    continue
                else:
                    # Both attempts failed
                    console.print(f"[yellow]Warning: Could not check for script updates: {e}[/yellow]")
                    return None

        return None

    def download_script_update(self, target_path: Path) -> bool:
        """Download the latest version of the script."""
        # Try with SSL verification first, then without if it fails
        ssl_configs = [
            {"verify": True, "timeout": 30},
            {"verify": False, "timeout": 30}
        ]

        for i, config in enumerate(ssl_configs):
            try:
                if i == 1:
                    console.print("[yellow]Retrying script download without SSL verification...[/yellow]")

                response = requests.get(self.config.script_gist_url, **config)
                response.raise_for_status()

                target_path.write_text(response.text)
                target_path.chmod(0o755)  # Make executable

                console.print(f"[green]Downloaded updated script to {target_path}[/green]")
                if i == 1:
                    console.print("[yellow]Note: Downloaded without SSL verification[/yellow]")
                return True

            except Exception as e:
                if i == 0:
                    # First attempt failed, try without SSL
                    continue
                else:
                    # Both attempts failed
                    console.print(f"[red]Failed to download script update: {e}[/red]")
                    return False

        return False
