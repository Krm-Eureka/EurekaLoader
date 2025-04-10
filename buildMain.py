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

def install_dependencies():
    """Install required dependencies from requirements.txt."""
    try:
        requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def build_app():
    """Build the application using PyInstaller."""
    try:
        ensure_pip()  # Ensure pip is available
        install_dependencies()  # Install dependencies

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
            "--name=EurekaLoader_P1_3",  # Set the output executable name
            "MainEurekaLoader.py"
        ])

        print("Application built successfully!")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except subprocess.CalledProcessError as e:
        print(f"Error building application: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    build_app()