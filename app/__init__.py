from flask import Flask
from app.api import api_bp
from app.ui import ui_bp
from app.lib.camera.camera_manager import CameraManager
from app.lib.camera.motion_detector import MotionDetector
from app.lib.notification.webhook_notifier import WebhookNotifier
from app.lib.notification.logging_notifier import LoggingNotifier
import yaml
import json
import os
import shutil

motion_detector = None

def create_app(config_file=None):
    # Define paths for the base and existing config files
    default_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.default.yml")
    existing_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config/config.yml")

    # Use the existing config file if none is provided
    if not config_file:
        config_file = existing_config_file

    # If the main config file doesn't exist, copy the base config file to it
    if not os.path.exists(config_file):
        if os.path.exists(default_config_file):
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            shutil.copy(default_config_file, config_file)
            print(f"Copied '{default_config_file}' to '{config_file}'")
        else:
            raise RuntimeError(f"Default configuration file '{default_config_file}' not found.")

    app = Flask(__name__)

    # Load configuration from the specified file
    try:
        with open(config_file, 'r') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            print(json.dumps(data, indent=4))
            app.config.update(data)
    except FileNotFoundError:
        raise RuntimeError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML file: {e}")

    # Initialize the notifiers and other app components
    logging_notifier = LoggingNotifier()
    webhook_notifier = WebhookNotifier(app.config["notification"])
    
    app.config["camera_manager"] = CameraManager(
        video_dir=app.config["capture"]["directory"],
        encoder_bitrate=app.config["capture"]["bitrate"],
    )

    app.config["motion_detector"] = MotionDetector(
        camera_manager=app.config["camera_manager"],
        motion_threshold=app.config["motion"]["mse_threshold"],
        max_encoding_time=app.config["motion"]["motion_gap"],
        notifiers=[logging_notifier, webhook_notifier]
    )

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    return app
