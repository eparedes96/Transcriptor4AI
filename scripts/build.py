from __future__ import annotations

"""
Build Automation Engine for Transcriptor4AI.

Orchestrates the standalone executable generation using PyInstaller.
Handles resource bundling, cross-platform path resolution, and 
automated cleanup of build artifacts.
"""

import os
import platform
import shutil
import sys

import PyInstaller.__main__

# -----------------------------------------------------------------------------
# ARTIFACT MANAGEMENT
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


# -----------------------------------------------------------------------------
# BUILD EXECUTION LOGIC
# -----------------------------------------------------------------------------

def build() -> None:
    """
    Configure and execute the PyInstaller compilation pipeline.

    Resolves project root dynamically, manages multi-platform separators,
    and bundles essential resources (locales, icons, and sidecar utilities).
    """
    print("======================================================")
    print("Starting Build Process for Transcriptor4AI")
    print("======================================================")

    # Prepare environment
    _clean_artifacts()

    # Resolve platform-specific data separators
    sep = ';' if platform.system() == 'Windows' else ':'

    # Resolve filesystem hierarchy
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    src_dir = os.path.join(project_root, "src")
    assets_dir = os.path.join(project_root, "assets")
    scripts_dir = os.path.join(project_root, "scripts")

    main_entry = os.path.join(src_dir, "transcriptor4ai", "main.py")

    # Resource definitions (Internal package structure)
    locales_src = os.path.join(src_dir, "transcriptor4ai", "interface", "locales", "*.json")
    locales_dest = os.path.join("transcriptor4ai", "interface", "locales")

    updater_src = os.path.join(scripts_dir, "updater.py")

    # PyInstaller data bundling arguments
    data_args = [
        f"{locales_src}{sep}{locales_dest}",
        f"{updater_src}{sep}."
    ]

    icon_path = os.path.join(assets_dir, "icon.ico")

    # Pipeline configuration for standalone binary
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

    # Map resources into the binary VFS
    for data in data_args:
        args.append(f'--add-data={data}')

    # Visual branding configuration
    if os.path.exists(icon_path):
        print(f"[*] Icon found: {icon_path}")
        args.append(f'--icon={icon_path}')
    else:
        print("[!] WARNING: Icon not found. Using default.")

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