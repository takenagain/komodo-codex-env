"""
Container Engine Abstraction for Integration Tests

Provides a unified interface for Docker and Podman container operations,
allowing tests to work with either container engine based on configuration.
"""

import os
import subprocess
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class ContainerEngineError(Exception):
    """Exception raised for container engine operations."""
    pass


class ContainerEngine:
    """Abstraction layer for container engine operations (Docker/Podman)."""
    
    def __init__(self, engine: Optional[str] = None):
        """
        Initialize container engine.
        
        Args:
            engine: Container engine to use ('docker' or 'podman'). 
                   If None, will auto-detect or use environment variable.
        """
        self.engine = self._determine_engine(engine)
        self._validate_engine()
        logger.info(f"Using container engine: {self.engine}")
    
    def _determine_engine(self, engine: Optional[str]) -> str:
        """Determine which container engine to use."""
        # 1. Use explicitly provided engine
        if engine:
            return engine.lower()
        
        # 2. Check environment variable
        env_engine = os.getenv('CONTAINER_ENGINE', '').lower()
        if env_engine in ['docker', 'podman']:
            return env_engine
        
        # 3. Auto-detect based on availability
        return self._auto_detect_engine()
    
    def _auto_detect_engine(self) -> str:
        """Auto-detect available container engine."""
        # Try Docker first (most common)
        if self._is_engine_available('docker'):
            return 'docker'
        
        # Fall back to Podman
        if self._is_engine_available('podman'):
            return 'podman'
        
        # Default to docker (will fail validation if not available)
        return 'docker'
    
    def _is_engine_available(self, engine: str) -> bool:
        """Check if a container engine is available."""
        try:
            result = subprocess.run(
                [engine, '--version'], 
                capture_output=True, 
                check=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _validate_engine(self) -> None:
        """Validate that the selected engine is available."""
        if not self._is_engine_available(self.engine):
            raise ContainerEngineError(
                f"Container engine '{self.engine}' is not available. "
                f"Please install {self.engine} or set CONTAINER_ENGINE to an available engine."
            )
    
    def _run_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a container command with the selected engine."""
        full_cmd = [self.engine] + cmd[1:]  # Replace first element with selected engine
        
        # Apply engine-specific adjustments
        full_cmd = self._adjust_command_for_engine(full_cmd)
        
        try:
            return subprocess.run(full_cmd, **kwargs)
        except subprocess.CalledProcessError as e:
            logger.error(f"Container command failed: {' '.join(full_cmd)}")
            logger.error(f"Exit code: {e.returncode}")
            if hasattr(e, 'stdout') and e.stdout:
                logger.error(f"STDOUT: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"STDERR: {e.stderr}")
            raise ContainerEngineError(f"Container command failed: {e}")
    
    def _adjust_command_for_engine(self, cmd: List[str]) -> List[str]:
        """Apply engine-specific command adjustments."""
        if self.engine == 'podman':
            return self._adjust_for_podman(cmd)
        return cmd
    
    def _adjust_for_podman(self, cmd: List[str]) -> List[str]:
        """Apply Podman-specific adjustments."""
        adjusted_cmd = cmd.copy()
        
        # Handle Podman-specific considerations
        if len(cmd) > 1:
            subcommand = cmd[1]
            
            if subcommand == 'run':
                # Podman may need different security context handling
                # Add --security-opt if privileged containers are needed
                if '--privileged' in cmd:
                    # Podman handles privileged containers slightly differently
                    pass
                
                # Podman may handle tmpfs mounts differently
                # The current tmpfs syntax should work for both
                pass
            
            elif subcommand == 'exec':
                # Podman exec works the same as Docker
                pass
            
            elif subcommand == 'build':
                # Add Podman-specific build optimizations if needed
                pass
        
        return adjusted_cmd
    
    # Public API methods
    
    def is_available(self) -> bool:
        """Check if the container engine is available."""
        return self._is_engine_available(self.engine)
    
    def version(self) -> str:
        """Get container engine version."""
        try:
            result = self._run_command([self.engine, '--version'], capture_output=True, text=True)
            return result.stdout.strip()
        except ContainerEngineError:
            return "unknown"
    
    def build(self, tag: str, dockerfile: str, context: str, **kwargs) -> subprocess.CompletedProcess:
        """Build a container image."""
        cmd = [self.engine, 'build', '-t', tag, '-f', dockerfile, context]
        return self._run_command(cmd, **kwargs)
    
    def run(self, image: str, command: Optional[List[str]] = None, 
            name: Optional[str] = None, detach: bool = False,
            environment: Optional[Dict[str, str]] = None,
            volumes: Optional[List[str]] = None,
            ports: Optional[List[str]] = None,
            extra_args: Optional[List[str]] = None,
            **kwargs) -> subprocess.CompletedProcess:
        """Run a container."""
        cmd = [self.engine, 'run']
        
        if detach:
            cmd.append('-d')
        
        if name:
            cmd.extend(['--name', name])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['--env', f'{key}={value}'])
        
        if volumes:
            for volume in volumes:
                cmd.extend(['-v', volume])
        
        if ports:
            for port in ports:
                cmd.extend(['-p', port])
        
        if extra_args:
            cmd.extend(extra_args)
        
        cmd.append(image)
        
        if command:
            cmd.extend(command)
        
        return self._run_command(cmd, **kwargs)
    
    def exec(self, container: str, command: List[str], 
             user: Optional[str] = None, interactive: bool = False,
             **kwargs) -> subprocess.CompletedProcess:
        """Execute command in running container."""
        cmd = [self.engine, 'exec']
        
        if user:
            cmd.extend(['-u', user])
        
        if interactive:
            cmd.append('-it')
        
        cmd.append(container)
        cmd.extend(command)
        
        return self._run_command(cmd, **kwargs)
    
    def cp(self, src: str, dest: str, **kwargs) -> subprocess.CompletedProcess:
        """Copy files between host and container."""
        cmd = [self.engine, 'cp', src, dest]
        return self._run_command(cmd, **kwargs)
    
    def rm(self, container: str, force: bool = False, **kwargs) -> subprocess.CompletedProcess:
        """Remove container."""
        cmd = [self.engine, 'rm']
        
        if force:
            cmd.append('-f')
        
        cmd.append(container)
        return self._run_command(cmd, **kwargs)
    
    def logs(self, container: str, **kwargs) -> subprocess.CompletedProcess:
        """Get container logs."""
        cmd = [self.engine, 'logs', container]
        return self._run_command(cmd, **kwargs)
    
    def ps(self, all_containers: bool = False, **kwargs) -> subprocess.CompletedProcess:
        """List containers."""
        cmd = [self.engine, 'ps']
        
        if all_containers:
            cmd.append('-a')
        
        return self._run_command(cmd, **kwargs)
    
    def stop(self, container: str, **kwargs) -> subprocess.CompletedProcess:
        """Stop container."""
        cmd = [self.engine, 'stop', container]
        return self._run_command(cmd, **kwargs)


def get_container_engine() -> ContainerEngine:
    """Get a configured container engine instance."""
    return ContainerEngine()


def container_available() -> bool:
    """Check if any container engine is available."""
    try:
        engine = get_container_engine()
        return engine.is_available()
    except ContainerEngineError:
        return False