"""Parallel execution and dependency management."""

import asyncio
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from rich.console import Console

console = Console()


class JobManager:
    """Manages parallel job execution with dependency tracking."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.jobs: Dict[str, asyncio.Task] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        
    def add_job(
        self, 
        name: str, 
        func: Callable,
        dependencies: Optional[List[str]] = None,
        *args,
        **kwargs
    ):
        """Add a job with optional dependencies."""
        if dependencies is None:
            dependencies = []
        
        self.dependencies[name] = set(dependencies)
        
        async def job_wrapper():
            # Wait for dependencies
            for dep in dependencies:
                while dep not in self.completed and dep not in self.failed:
                    if dep in self.failed:
                        raise RuntimeError(f"Dependency {dep} failed")
                    await asyncio.sleep(0.1)
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                self.completed.add(name)
                return result
            except Exception as e:
                self.failed.add(name)
                console.print(f"[red]Job {name} failed: {e}[/red]")
                raise
        
        return job_wrapper
    
    async def run_job(self, name: str, func: Callable, dependencies: Optional[List[str]] = None, *args, **kwargs):
        """Run a single job."""
        job = self.add_job(name, func, dependencies, *args, **kwargs)
        self.jobs[name] = asyncio.create_task(job())
        return await self.jobs[name]
    
    async def run_all_jobs(self):
        """Run all added jobs."""
        if not self.jobs:
            return
        
        try:
            await asyncio.gather(*self.jobs.values())
        except Exception as e:
            console.print(f"[red]One or more jobs failed: {e}[/red]")
            # Cancel remaining jobs
            for task in self.jobs.values():
                if not task.done():
                    task.cancel()
            raise


class CommandExecutor:
    """Executes shell commands with proper error handling and logging."""
    
    def __init__(self, parallel_execution: bool = True, max_workers: int = 4):
        self.parallel_execution = parallel_execution
        self.max_workers = max_workers
        self.job_manager = JobManager(max_workers)
    
    def run_command(
        self, 
        command: str, 
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        check: bool = True,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute a shell command."""
        console.print(f"[blue]Executing:[/blue] {command}")
        if cwd:
            console.print(f"[blue]In directory:[/blue] {cwd}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                timeout=timeout,
                check=check,
                capture_output=capture_output,
                text=True
            )
            
            if result.stdout and capture_output:
                console.print(f"[green]Output:[/green] {result.stdout.strip()}")
            
            return result
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f"\nError: {e.stderr.strip()}"
            console.print(f"[red]{error_msg}[/red]")
            raise
        except subprocess.TimeoutExpired as e:
            console.print(f"[red]Command timed out after {timeout} seconds[/red]")
            raise
    
    async def run_command_async(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        check: bool = True
    ) -> str:
        """Execute a shell command asynchronously."""
        console.print(f"[blue]Executing async:[/blue] {command}")
        if cwd:
            console.print(f"[blue]In directory:[/blue] {cwd}")
        
        try:
            if cwd:
                # Change to directory before running command
                full_command = f"cd {cwd} && {command}"
            else:
                full_command = command
            
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            
            if process.returncode != 0 and check:
                error_msg = f"Command failed with exit code {process.returncode}"
                if stderr_str:
                    error_msg += f"\nError: {stderr_str}"
                console.print(f"[red]{error_msg}[/red]")
                raise subprocess.CalledProcessError(process.returncode, command, stderr_str)
            
            if stdout_str:
                console.print(f"[green]Output:[/green] {stdout_str}")
            
            return stdout_str
            
        except asyncio.TimeoutError:
            console.print(f"[red]Command timed out after {timeout} seconds[/red]")
            raise
    
    def run_parallel(self, commands: List[tuple], timeout: Optional[int] = None):
        """Run multiple commands in parallel using ThreadPoolExecutor."""
        if not self.parallel_execution or len(commands) == 1:
            # Run sequentially
            results = []
            for cmd_info in commands:
                if len(cmd_info) == 2:
                    command, cwd = cmd_info
                else:
                    command = cmd_info[0]
                    cwd = None
                
                result = self.run_command(command, cwd=cwd, timeout=timeout)
                results.append(result)
            return results
        
        # Run in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_cmd = {}
            
            for cmd_info in commands:
                if len(cmd_info) == 2:
                    command, cwd = cmd_info
                else:
                    command = cmd_info[0]
                    cwd = None
                
                future = executor.submit(
                    self.run_command, command, cwd=cwd, timeout=timeout
                )
                future_to_cmd[future] = command
            
            for future in as_completed(future_to_cmd):
                command = future_to_cmd[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    console.print(f"[red]Command '{command}' failed: {e}[/red]")
                    raise
        
        return results
    
    async def run_with_dependencies(
        self,
        name: str,
        command: str,
        dependencies: Optional[List[str]] = None,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None
    ):
        """Run a command with dependency management."""
        return await self.job_manager.run_job(
            name,
            self.run_command_async,
            dependencies,
            command,
            cwd=cwd,
            timeout=timeout
        )
    
    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system."""
        try:
            result = self.run_command(
                f"command -v {command}",
                check=False,
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_command_version(self, command: str, version_arg: str = "--version") -> Optional[str]:
        """Get the version of a command."""
        try:
            result = self.run_command(
                f"{command} {version_arg}",
                check=False,
                capture_output=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
