from __future__ import annotations

"""
Application Layer Facade.

Centralizes access to the core logic services and orchestrators. This layer 
implements the system's use cases by coordinating domain entities and 
infrastructure adapters through injected ports.

Categories:
1. PIPELINE: High-level workflow orchestration.
2. ANALYSIS: Static inspection (AST) and project mapping.
3. PROCESSING: LLM-specific token counting and estimation.
4. TRANSFORMATION: Security sanitization and code optimization.
5. SERVICES: Supporting cross-cutting concerns (Cost, Scanning, Updates).
"""

# ==============================================================================
# PIPELINE ORCHESTRATION
# ==============================================================================
from transcriptor4ai.application.pipeline.orchestrator import run_pipeline

# ==============================================================================
# ANALYSIS SERVICES (AST & STRUCTURE)
# ==============================================================================
from transcriptor4ai.application.analysis.ast_parser import (
    extract_definitions,
    generate_skeleton_code,
)
from transcriptor4ai.application.analysis.tree_generator import generate_directory_tree

# ==============================================================================
# PROCESSING SERVICES (TOKENIZATION)
# ==============================================================================
from transcriptor4ai.application.processing.token_service import (
    TokenizerService,
    count_tokens,
)

# ==============================================================================
# TRANSFORMATION SERVICES (REFACTORED)
# ==============================================================================
from transcriptor4ai.application.transformation.code_minifier import CodeMinifierService
from transcriptor4ai.application.transformation.privacy_sanitizer import (
    PrivacySanitizerService,
)

# ==============================================================================
# CROSS-CUTTING SERVICES
# ==============================================================================
from transcriptor4ai.application.services.cost_calculator import CostCalculatorService
from transcriptor4ai.application.services.project_scanner import ProjectScannerService
from transcriptor4ai.application.services.update_service import UpdateManager

__all__ = [
    # Pipeline
    "run_pipeline",
    # Analysis
    "extract_definitions",
    "generate_skeleton_code",
    "generate_directory_tree",
    # Processing
    "TokenizerService",
    "count_tokens",
    # Transformation
    "CodeMinifierService",
    "PrivacySanitizerService",
    # Services
    "CostCalculatorService",
    "ProjectScannerService",
    "UpdateManager",
]