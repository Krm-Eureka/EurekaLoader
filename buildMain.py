import os
import sys
import subprocess
import platform
import shutil


def ensure_pip():
    """Ensure pip is installed and available."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])


def install_dependencies():
    """Install required dependencies from requirements.txt."""
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(requirements_path):
        print("⚠ requirements.txt not found. Skipping dependency installation.")
        return
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        sys.exit(1)


def clean_build_artifacts():
    """Remove old build artifacts before building."""
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)
    spec_file = "EurekaLoader.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)


def build_app():
    try:
        print("🔧 Ensuring pip is available...")
        ensure_pip()

        print("📦 Installing dependencies...")
        install_dependencies()

        print("🧼 Cleaning previous builds...")
        clean_build_artifacts()

        print("🛠 Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

        sep = ';' if platform.system() == 'Windows' else ':'

        # ✅ ตรวจสอบไฟล์ที่ต้องใช้ก่อน build
        required_files = ["config.ini", "favicon.ico", "EA_Logo.png"]
        missing_files = [f for f in required_files if not os.path.isfile(f)]
        if missing_files:
            print(f"❌ Missing required files: {', '.join(missing_files)}")
            sys.exit(1)

        print("🚀 Building application with PyInstaller...")
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed",
            "--icon=favicon.ico",
            f"--add-data=config.ini{sep}.",
            f"--add-data=favicon.ico{sep}.",
            f"--add-data=EA_Logo.png{sep}.",
            "--name=EurekaLoader",
            "MainEurekaLoader.py"
        ])

        print("✅ Build complete! Output in /dist/EurekaLoader/")

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Subprocess error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    build_app()
