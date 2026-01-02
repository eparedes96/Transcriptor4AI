import PyInstaller.__main__
import os
import platform
import shutil


def clean_artifacts():
    """Remove previous build artifacts to ensure a clean build."""
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning {folder}...")
            shutil.rmtree(folder)

    spec_file = "transcriptor4ai.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def build():
    print("Starting Build Process for Transcriptor4AI...")

    # 1. Clean previous builds
    clean_artifacts()

    # 2. Determine OS path separator for --add-data
    sep = ';' if platform.system() == 'Windows' else ':'

    # 3. Define Data Resources
    locales_src = os.path.join("src", "transcriptor4ai", "locales", "*.json")
    locales_dest = os.path.join("transcriptor4ai", "locales")
    add_data_arg = f"{locales_src}{sep}{locales_dest}"

    # 4. Define Icon Path
    icon_path = os.path.join("assets", "icon.ico")

    # 5. Base PyInstaller Arguments
    args = [
        'main.py',
        '--name=transcriptor4ai',
        '--onefile',
        '--console',
        '--paths=src',
        f'--add-data={add_data_arg}',
        '--clean',
    ]

    # 6. Conditionally add Icon
    if os.path.exists(icon_path):
        print(f"Icon found: {icon_path}")
        args.append(f'--icon={icon_path}')
    else:
        print("WARNING: Icon not found in 'assets/icon.ico'. Building with default icon.")

    print(f"Running PyInstaller with args: {args}")

    # 7. Execute
    PyInstaller.__main__.run(args)

    print("\nBuild Complete! Check the 'dist/' folder.")


if __name__ == "__main__":
    build()