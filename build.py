import os
import subprocess
import sys

def ensure_pip():
    """Ensure pip is installed and available."""
    try:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError as e:
        print(f"Error ensuring pip: {e}")
        sys.exit(1)

def build_app():
    """Builds the application using PyInstaller."""
    try:
        ensure_pip()  # Ensure pip is available

        # Install PyInstaller if not already installed
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

        # Build the application
        subprocess.check_call([
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--icon=favicon.ico",  # Add your icon file here
            "--add-data=config.ini;.",  # Include config.ini
            "--add-data=favicon.ico;.",  # Include favicon.ico
            "--add-data=forimport.csv;.",  # Include forimport.csv
            "--name=EurekaLoader",  # Set the output executable name
            "MainEurekaLoader_Prototype.py"
        ])

        print("Application built successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error building application: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    build_app()