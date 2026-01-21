from __future__ import annotations

"""
Build Automation Engine for Transcriptor4AI.

Orchestrates the standalone executable generation using PyInstaller.
Handles resource bundling, cross-platform path resolution, and 
automated cleanup of build artifacts. Integrates a pre-build hook 
to inject the latest model metadata snapshot (LiteLLM).
"""

import json
import os
import platform
import shutil
import sys

import PyInstaller.__main__
import requests

# -----------------------------------------------------------------------------
# BUILD CONSTANTS
# -----------------------------------------------------------------------------

MODEL_DATA_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)


# -----------------------------------------------------------------------------
# PRIVATE ARTIFACT HELPERS
# -----------------------------------------------------------------------------

def _clean_artifacts() -> None:
    """
    Remove residual build artifacts to ensure an idempotent build process.

    Targets standard PyInstaller output directories and the generated
    spec file to prevent cached configuration leaks.
    """
    folders_to_clean = ["build", "dist"]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"[*] Cleaning {folder}...")
            shutil.rmtree(folder)

    spec_file = "transcriptor4ai.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def _download_latest_snapshot(dest_path: str) -> bool:
    """
    Acquire the latest model authority JSON prior to compilation.

    Ensures the standalone binary is packaged with up-to-date model
    pricing and context window definitions.

    Args:
        dest_path: Target filesystem path for the snapshot.

    Returns:
        bool: True if the snapshot was successfully acquired and persisted.
    """
    print(f"[*] Downloading latest model snapshot from LiteLLM...")
    try:
        response = requests.get(MODEL_DATA_URL, timeout=15)
        response.raise_for_status()

        # Validate JSON integrity
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Downloaded metadata is not a valid JSON object.")

        # Ensure assets directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(',', ':'))

        size_kb = os.path.getsize(dest_path) / 1024
        print(f"[+] Snapshot injected successfully ({size_kb:.1f} KB).")
        return True

    except Exception as e:
        print(f"[!] WARNING: Failed to download fresh snapshot: {e}")
        print("[!] The build will proceed with the existing local assets if available.")
        return False


# -----------------------------------------------------------------------------
# PUBLIC API: BUILD EXECUTION
# -----------------------------------------------------------------------------

def build() -> None:
    """
    Configure and execute the PyInstaller compilation pipeline.

    Resolves project root dynamically, manages multi-platform separators,
    and bundles essential resources including the dynamic model snapshot.
    """
    print("======================================================")
    print("Starting Build Process for Transcriptor4AI v2.2.0")
    print("======================================================")

    # 1. Environment Preparation
    _clean_artifacts()

    # 2. Path Resolution
    sep = ';' if platform.system() == 'Windows' else ':'

    # Resolve filesystem hierarchy
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    src_dir = os.path.join(project_root, "src")
    assets_dir = os.path.join(project_root, "src", "transcriptor4ai", "assets")
    scripts_dir = os.path.join(project_root, "scripts")

    # 3. Dynamic Data Injection (Fase 1: Snapshot Strategy)
    bundled_json_path = os.path.join(assets_dir, "bundled_models.json")
    _download_latest_snapshot(bundled_json_path)

    # 4. Binary Configuration
    main_entry = os.path.join(src_dir, "transcriptor4ai", "main.py")

    # Resource Mapping (Internal package structure)
    locales_src = os.path.join(src_dir, "transcriptor4ai", "interface", "locales", "*.json")
    locales_dest = os.path.join("transcriptor4ai", "interface", "locales")

    assets_src = os.path.join(assets_dir, "*.json")
    assets_dest = os.path.join("transcriptor4ai", "assets")

    updater_src = os.path.join(scripts_dir, "updater.py")

    # PyInstaller data bundling arguments
    data_args = [
        f"{locales_src}{sep}{locales_dest}",
        f"{assets_src}{sep}{assets_dest}",
        f"{updater_src}{sep}."
    ]

    icon_path = os.path.join(project_root, "assets", "icon.ico")

    # Compilation Arguments
    args = [
        main_entry,
        '--name=transcriptor4ai',
        '--onefile',
        '--console',
        f'--paths={src_dir}',
        '--clean',
        '--collect-submodules=requests',
        '--collect-all=customtkinter',
        '--collect-all=tkinterdnd2',
    ]

    # Map assets and locales into the VFS
    for data in data_args:
        args.append(f'--add-data={data}')

    # Visual branding configuration
    if os.path.exists(icon_path):
        print(f"[*] Icon found: {icon_path}")
        args.append(f'--icon={icon_path}')

    # 5. Pipeline Execution
    print("[*] Running PyInstaller with configured paths...")
    try:
        PyInstaller.__main__.run(args)
        print("\n[+] Build Successful! Executable located in 'dist/' folder.")
    except Exception as e:
        print(f"\n[!] CRITICAL BUILD FAILURE: {e}", file=sys.stderr)
        sys.exit(1)


# -----------------------------------------------------------------------------
# SCRIPT ENTRYPOINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    build()