from flask import Flask
from app.api import api_bp
from app.ui import ui_bp
import yaml

def create_app(config_file="config.yml"):
    app = Flask(__name__)

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML file: {e}")

    # Map YAML keys to Flask app config
    for section, values in config.items():
        for key, value in values.items():
            app.config[f"{section.upper()}_{key.upper()}"] = value

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    return app

def _parse_value(value):
    """Helper function to parse YAML values into their appropriate types."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value