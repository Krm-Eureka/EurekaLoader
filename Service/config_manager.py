import os
import configparser

def get_base_dir():
    """Determine the base directory from config.ini."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    print(f"Base directory: {base_dir}")
    config_path = os.path.join(base_dir, "config.ini")
    config = configparser.ConfigParser()

    if not os.path.exists(config_path):
        raise RuntimeError(f"Config file not found: {config_path}")

    config.read(config_path, encoding="utf-8")

    if config.has_option("Paths", "base_dir"):
        return config.get("Paths", "base_dir")
    else:
        raise RuntimeError("base_dir not defined in config.ini")

def load_config():
    """Load or create the configuration file."""
    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, "config.ini")
    config = configparser.ConfigParser()

    if not os.path.exists(config_path):
        # Create a default config file if it doesn't exist
        with open(config_path, "w", encoding="utf-8") as config_file:
            config.add_section("Paths")
            config.set("Paths", "base_dir", base_dir)
            config.set("Paths", "import_csv_path", "./Data/forimport.csv")
            config.set("Paths", "export_dir", "./Data")
            config.add_section("UI")
            config.set("UI", "background_color", "#f0f0f0")
            config.set("UI", "window_width", "800")
            config.set("UI", "window_height", "600")
            config.write(config_file)
            raise RuntimeError(
                f"Config file created at {config_path}. Please edit it before running the program."
            )

    config.read(config_path, encoding="utf-8")

    # Resolve relative paths to absolute paths
    for key in ["import_csv_path", "export_dir"]:
        if config.has_option("Paths", key):
            relative_path = config.get("Paths", key)
            absolute_path = os.path.abspath(os.path.join(base_dir, relative_path))
            config.set("Paths", key, absolute_path)

    return config, base_dir