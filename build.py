from __future__ import annotations

"""
Industrial-grade Build Script for Transcriptor4AI.

Automates the creation of a standalone executable using PyInstaller.
Handles data resources (locales), icons, and dependency collection
for network-enabled features.
"""

import os
import platform
import shutil
import sys
import PyInstaller.__main__


def _clean_artifacts() -> None:
    """Remove previous build artifacts to ensure a clean build environment."""
    folders_to_clean = ["build", "dist"]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"[*] Cleaning {folder}...")
            shutil.rmtree(folder)

    spec_file = "transcriptor4ai.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def build() -> None:
    """
    Configure and execute the PyInstaller build process.
    """
    print("======================================================")
    print("Starting Build Process for Transcriptor4AI")
    print("======================================================")

    # 1. Environment Preparation
    _clean_artifacts()

    # 2. Resource Path Management
    sep = ';' if platform.system() == 'Windows' else ':'

    # Locales (Translations)
    locales_src = os.path.join("src", "transcriptor4ai", "locales", "*.json")
    locales_dest = os.path.join("transcriptor4ai", "locales")

    # Sidecar Updater (Included as data to be extracted or run externally)
    updater_src = "updater.py"

    data_args = [
        f"{locales_src}{sep}{locales_dest}",
        f"{updater_src}{sep}."
    ]

    # 3. Branding (Icon)
    icon_path = os.path.join("assets", "icon.ico")

    # 4. PyInstaller Configuration
    args = [
        'main.py',
        '--name=transcriptor4ai',
        '--onefile',
        '--console',
        '--paths=src',
        '--clean',
        '--collect-submodules=requests',
        '--collect-submodules=PySimpleGUI',
    ]

    # Add data resources
    for data in data_args:
        args.append(f'--add-data={data}')

    # Add icon if available
    if os.path.exists(icon_path):
        print(f"[*] Icon found: {icon_path}")
        args.append(f'--icon={icon_path}')
    else:
        print("[!] WARNING: Icon not found in 'assets/icon.ico'. Using default.")

    # 5. Execution
    print(f"[*] Running PyInstaller with following configuration...")
    try:
        PyInstaller.__main__.run(args)
        print("\n[+] Build Successful! Executable located in 'dist/' folder.")
    except Exception as e:
        print(f"\n[!] CRITICAL BUILD FAILURE: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build()