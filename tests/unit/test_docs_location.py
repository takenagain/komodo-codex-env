#!/usr/bin/env python3
"""
Simple test to check where documentation files are created.
"""

import subprocess
import tempfile
import os
from pathlib import Path


def test_fetch_docs_locally():
    """Test the fetch-docs command locally to see where files are created."""
    
    # Create a temporary directory to test in
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Testing in temporary directory: {temp_path}")
        
        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_path)
        
        try:
            # Run the fetch-docs command
            cmd = [
                "python3", "-m", "komodo_codex_env.cli", 
                "fetch-docs", 
                "--target", str(temp_path),
                "--kdf-docs"
            ]
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(original_cwd) / "src")
            
            print(f"Running command: {' '.join(cmd)}")
            print(f"Working directory: {temp_path}")
            print(f"PYTHONPATH: {env['PYTHONPATH']}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                env=env,
                cwd=original_cwd  # Run from original directory but target temp
            )
            
            print(f"Exit code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            
            # List files in temp directory
            print(f"\nFiles created in {temp_path}:")
            for item in temp_path.rglob("*"):
                if item.is_file():
                    print(f"  {item.relative_to(temp_path)}")
                    
            # Check for specific files
            agents_file = temp_path / "AGENTS.md"
            kdf_file = temp_path / "KDF_API_DOCUMENTATION.md"
            
            print(f"\nAGENTS.md exists: {agents_file.exists()}")
            print(f"KDF_API_DOCUMENTATION.md exists: {kdf_file.exists()}")
            
            if agents_file.exists():
                print(f"AGENTS.md size: {agents_file.stat().st_size} bytes")
            if kdf_file.exists():
                print(f"KDF_API_DOCUMENTATION.md size: {kdf_file.stat().st_size} bytes")
                
        finally:
            os.chdir(original_cwd)


def test_current_directory():
    """Test running fetch-docs in the current directory."""
    print("Testing fetch-docs in current directory...")
    
    original_cwd = os.getcwd()
    
    # Run the fetch-docs command
    cmd = [
        "python3", "-m", "komodo_codex_env.cli", 
        "fetch-docs", 
        "--kdf-docs"
    ]
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {original_cwd}")
    
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True,
        env=env
    )
    
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    # Check for files in current directory
    current_path = Path(".")
    agents_file = current_path / "AGENTS.md"
    kdf_file = current_path / "KDF_API_DOCUMENTATION.md"
    
    print(f"\nAGENTS.md exists in current dir: {agents_file.exists()}")
    print(f"KDF_API_DOCUMENTATION.md exists in current dir: {kdf_file.exists()}")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING DOCUMENTATION FETCH BEHAVIOR")
    print("=" * 60)
    
    test_current_directory()
    
    print("\n" + "=" * 60)
    
    test_fetch_docs_locally()
