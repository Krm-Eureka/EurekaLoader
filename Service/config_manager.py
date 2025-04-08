import os
import sys
import configparser

def get_base_dir():
    """Determine the base directory."""
    if getattr(sys, 'frozen', False):  
        return "D:/EurekaLoader"
    return os.path.dirname(os.path.abspath(__file__))

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
            config.set("Paths", "default_csv_path", "./Input/forimport.csv")
            config.add_section("UI")
            config.set("UI", "background_color", "#f0f0f0")
            config.set("UI", "window_width", "800")
            config.set("UI", "window_height", "600")
            config.write(config_file)
            print(f"Config file created at {config_path}. Please edit it before running the program.")
            sys.exit(1)

    config.read(config_path, encoding="utf-8")
    return config