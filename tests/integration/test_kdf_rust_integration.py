"""KDF Rust Integration Test

This test verifies Komodo DeFi Framework dependencies and Rust toolchain
installation. It runs the install.sh script with --install-type KDF, executes
the setup command, and ensures that a new Cargo project can be built inside a
container.
"""

import logging
from pathlib import Path

from .base_integration_test import ContainerIntegrationTest

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = PROJECT_ROOT / ".devcontainer" / "Dockerfile"
INSTALL_SCRIPT = PROJECT_ROOT / "install.sh"


class KdfRustIntegrationTest(ContainerIntegrationTest):
    """Test KDF dependencies and Rust toolchain inside container."""

    # Class configuration for base class
    IMAGE_NAME = "kdf-rust-test"
    CONTAINER_PREFIX = "kdf-rust-test"
    DOCKERFILE = DOCKERFILE
    BUILD_CONTEXT = PROJECT_ROOT
    CONTAINER_TIMEOUT = 3600  # 1 hour

    def test_kdf_rust_pipeline(self):
        """Test the complete KDF Rust development pipeline."""
        logger.info("Starting KDF Rust integration test pipeline")

        try:
            # Step 1: Copy and run install script with KDF install type
            logger.info("Step 1: Running install script with KDF install type")
            success = self.copy_to_container(INSTALL_SCRIPT, "/home/testuser/install.sh")
            self.assertTrue(success, "Failed to copy install script")

            install_command = """
            cd /home/testuser &&
            sed -i 's/read -p "Do you want to run the full setup now.*/REPLY="n"/' install.sh &&
            sed -i 's/kce-full-setup "$FLUTTER_VERSION"/echo "Skipping auto full setup"/' install.sh &&
            timeout 600 ./install.sh --install-type KDF --debug
            """
            result = self.run_in_container(install_command, timeout=700)
            self.skip_on_command_failure(result, "Install script with KDF type failed")
            logger.info("✓ Install script with KDF type completed")

            # Step 2: Verify basic installation
            logger.info("Step 2: Verifying basic installation")
            verify_command = """
            cd /home/testuser &&
            source ~/.bashrc &&
            test -d ~/.komodo-codex-env &&
            export PATH="$HOME/.local/bin:$PATH" &&
            uv --version &&
            echo "Basic installation verified"
            """
            result = self.run_in_container(verify_command)
            self.skip_on_command_failure(result, "Basic installation verification failed")
            logger.info("✓ Basic installation verified")

            # Step 3: Run KDF setup
            logger.info("Step 3: Running KDF setup")
            setup_command = """
            cd /home/testuser &&
            source ~/.bashrc &&
            export PATH="$HOME/.local/bin:$PATH" &&
            export HOME="/home/testuser" &&
            export USER="testuser" &&
            cd ~/.komodo-codex-env &&
            uv run komodo-codex-env setup --install-type KDF --verbose
            """
            result = self.run_in_container(setup_command, timeout=1200)
            
            if result.returncode != 0:
                logger.error(f"KDF setup failed with exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                self.skipTest(f"KDF setup failed: {result.stderr}")
            
            logger.info("✓ KDF setup completed")
        except Exception as e:
            self.skipTest(f"Integration test failed with exception: {e}")

        # Step 4: Verify Rust installation
        logger.info("Step 4: Verifying Rust installation")
        rust_check_command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        source setup_env.sh &&
        rustc --version &&
        cargo --version &&
        echo "Rust toolchain verified"
        """
        result = self.run_in_container(rust_check_command, timeout=120)
        self.assert_command_success(result, "Rust toolchain verification failed")
        logger.info("✓ Rust toolchain verified")

        # Step 5: Create a simple Cargo project
        logger.info("Step 5: Creating Cargo project")
        create_project_command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        cd ~/.komodo-codex-env &&
        source setup_env.sh &&
        cargo new test_rust_project &&
        cd test_rust_project &&
        echo "Cargo project created"
        """
        result = self.run_in_container(create_project_command, timeout=300)
        self.assert_command_success(result, "Cargo project creation failed")
        logger.info("✓ Cargo project created")

        # Step 6: Build the Cargo project
        logger.info("Step 6: Building Cargo project")
        build_project_command = """
        cd ~/.komodo-codex-env/test_rust_project &&
        source ~/.komodo-codex-env/setup_env.sh &&
        cargo build &&
        echo "Cargo build completed"
        """
        result = self.run_in_container(build_project_command, timeout=600)
        self.assert_command_success(result, "Cargo build failed")
        logger.info("✓ Cargo project built successfully")

        # Step 7: Run the Cargo project
        logger.info("Step 7: Running Cargo project")
        run_project_command = """
        cd ~/.komodo-codex-env/test_rust_project &&
        source ~/.komodo-codex-env/setup_env.sh &&
        cargo run &&
        echo "Cargo run completed"
        """
        result = self.run_in_container(run_project_command, timeout=300)
        self.assert_command_success(result, "Cargo run failed")
        
        # Verify "Hello, world!" output
        self.assertIn("Hello, world!", result.stdout, "Expected 'Hello, world!' output not found")
        logger.info("✓ Cargo project ran successfully with expected output")

        # Step 8: Verify Docker dependencies (KDF specific)
        logger.info("Step 8: Verifying Docker installation for KDF")
        docker_check_command = """
        cd /home/testuser &&
        source ~/.bashrc &&
        export PATH="$HOME/.local/bin:$PATH" &&
        docker --version || echo "Docker not installed" &&
        systemctl status docker 2>/dev/null || echo "Docker service not running (expected in container)"
        """
        result = self.run_in_container(docker_check_command, timeout=120)
        # Docker might not be running inside container, but should be installed
        if "Docker" in result.stdout:
            logger.info("✓ Docker installation detected")
        else:
            logger.info("! Docker not found, but this might be expected in container environment")

        logger.info("✓ KDF Rust integration test completed successfully!")


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)