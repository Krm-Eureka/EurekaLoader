import os
import configparser

def ensure_path_exists(path):
    """Ensure the given path exists, create it if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path)

def load_config():
    """Load or create the configuration file.""" 
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, "config.ini")
    config = configparser.ConfigParser()

    if not os.path.exists(config_path):
        # Create a default config file if it doesn't exist
        with open(config_path, "w", encoding="utf-8") as config_file:
            config.add_section("Paths")
            config.set("Paths", "base_dir", base_dir)
            config.set("Paths", "data_path", os.path.join(base_dir, "Data"))
            config.add_section("UI")
            config.set("UI", "background_color", "#f0f0f0")
            config.set("UI", "window_width", "800")
            config.set("UI", "window_height", "600")
            config.write(config_file)

    config.read(config_path, encoding="utf-8")

    # Ensure paths exist
    ensure_path_exists(config.get("Paths", "data_path"))

    return config, base_dir