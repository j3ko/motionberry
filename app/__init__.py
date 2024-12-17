from flask import Flask
from app.api import api_bp
from app.ui import ui_bp
from app.lib.camera.motion_detector import MotionDetector
from app.lib.notification.webhook_notifier import WebhookNotifier
from app.lib.notification.logging_notifier import LoggingNotifier
import yaml
import json
import os

motion_detector = None

def create_app(config_file=None):
    if not config_file:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.yml")

    app = Flask(__name__)

    try:
        with open(config_file, 'r') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            print(json.dumps(data, indent=4))
            app.config.update(data)
    except FileNotFoundError:
        raise RuntimeError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML file: {e}")

    logging_notifier = LoggingNotifier()
    webhook_notifier = WebhookNotifier(app.config["notification"])

    app.config["motion_detector"] = MotionDetector(
        video_dir=app.config["recording"]["directory"],
        motion_threshold=app.config["motion"]["mse_threshold"],
        max_encoding_time=app.config["motion"]["motion_gap"],
        encoder_bitrate=app.config["recording"]["bitrate"],
        notifiers=[logging_notifier, webhook_notifier]
    )

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    return app