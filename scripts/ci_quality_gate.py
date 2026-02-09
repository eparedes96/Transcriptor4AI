from __future__ import annotations

"""
CI Quality Gate Orchestrator - Path Aware Version.

Centralizes execution of quality tools (Ruff, Mypy, Pytest) by 
dynamically resolving the project root to prevent path-related 
execution failures.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# ==============================================================================
# PATH RESOLUTION (Context Awareness)
# ==============================================================================

# 1. IDENTIFICATION: Get the absolute path of this script
SCRIPT_PATH = Path(__file__).resolve()

# 2. RESOLUTION: Project root is one level up from 'scripts/'
PROJECT_ROOT = SCRIPT_PATH.parent.parent

# 3. MAPPING: Define absolute paths for target directories
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ==============================================================================
# QUALITY GATE ENGINE
# ==============================================================================

class QualityGate:
    """
    Orchestrates sequential execution of code quality tools using
    absolute path context.
    """

    def __init__(self) -> None:
        self.failed_steps: List[str] = []

    def run_command(self, step_name: str, command: List[str]) -> bool:
        """
        Executes a shell command with the project root as CWD.

        Args:
            step_name: Name of the validation step.
            command: List of command arguments.

        Returns:
            bool: True if success.
        """
        logger.info(f"STARTING: {step_name}...")
        start_time = time.time()

        try:
            # EXECUTION: Injects PROJECT_ROOT as the working directory
            # so tools can find config files (pyproject.toml, etc.)
            result = subprocess.run(
                command,
                check=False,
                cwd=str(PROJECT_ROOT)
            )
            duration = time.time() - start_time

            if result.returncode == 0:
                logger.info(f"SUCCESS: {step_name} completed in {duration:.2f}s")
                return True

            logger.error(f"FAILED: {step_name} returned exit code {result.returncode}")
            self.failed_steps.append(step_name)
            return False

        except FileNotFoundError:
            logger.critical(f"CRITICAL: Tool for '{step_name}' not found.")
            self.failed_steps.append(f"{step_name} (Missing Tool)")
            return False

    def execute_all(self) -> int:
        """Runs the quality pipeline using absolute path references."""

        # 1. CHECK ENVIRONMENT: Ensure directories exist
        if not SRC_DIR.exists():
            logger.error(f"Critical error: {SRC_DIR} not found.")
            return 1

        # STEP 1: Linting
        self.run_command("Ruff Linting", ["ruff", "check", "src", "tests"])

        # STEP 2: Formatting Check
        self.run_command("Ruff Format Check", ["ruff", "format", "--check", "src", "tests"])

        # STEP 3: Type Analysis
        self.run_command("Mypy Type Analysis", ["mypy", "src"])

        # STEP 4: Test Suite
        if TESTS_DIR.exists():
            self.run_command("Pytest Suite", ["pytest", "tests"])
        else:
            logger.warning("Skipping tests: 'tests/' directory is missing.")

        return self._finalize_report()

    def _finalize_report(self) -> int:
        """Consolidates results."""
        print("\n" + "=" * 50)
        print("QUALITY GATE FINAL REPORT")
        print(f"Project Root: {PROJECT_ROOT}")
        print("=" * 50)

        if not self.failed_steps:
            logger.info("RESULT: PASSED. Code is production-ready.")
            return 0

        logger.error(f"RESULT: FAILED. Steps failed: {', '.join(self.failed_steps)}")
        return 1


# ==============================================================================
# ENTRYPOINT
# ==============================================================================

def main() -> None:
    """Execution entrypoint."""
    gate = QualityGate()
    exit_code = gate.execute_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\nExecution aborted.")
        sys.exit(130)