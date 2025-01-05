import logging
from flask.logging import default_handler
from flask import Flask, current_app
from app.api import api_bp
from app.ui import ui_bp
from app.lib.camera.file_manager import FileManager
from app.lib.camera.video_processor import VideoProcessor
from app.lib.camera.camera_manager import CameraManager
from app.lib.camera.stream_manager import StreamManager
from app.lib.camera.motion_detector import MotionDetector
from app.lib.camera.status_manager import StatusManager
from app.lib.notification.webhook_notifier import WebhookNotifier
from app.lib.notification.logging_notifier import LoggingNotifier
import yaml
import json
import os
import shutil
from .version import __version__

def create_app(config_file=None):
    # Temporary logging config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing Motionberry v{__version__}.")

    app = Flask(__name__)

    config = load_config(config_file)
    app.config.update(config)
    configure_logging(app, config)
    initialize_components(app, config)

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    app.logger.info("Application initialized successfully.")
    return app

def initialize_components(app, config):
    """Initialize application components."""
    logging_notifier = LoggingNotifier()
    webhook_notifier = WebhookNotifier(config.get("notification", {}))
    app.config["file_manager"] = FileManager(
        output_dir=str(config.get("capture", {}).get("directory", "captures")),
        max_size_mb=int(config.get("capture", {}).get("max_size_mb", None)),
        max_age_days=int(config.get("capture", {}).get("max_age_days", None)),
    )

    app.config["video_processor"] = VideoProcessor(
        file_manager=app.config["file_manager"],
        video_format=config.get("capture", {}).get("video_format", "mp4"),
    )

    app.config["camera_manager"] = CameraManager(
        file_manager=app.config["file_manager"],
        video_processor=app.config["video_processor"],
        encoder_bitrate=int(config.get("capture", {}).get("bitrate", 5000000)),
        record_size=tuple(config.get("capture", {}).get("record_size", [1024, 720])),
        detect_size=tuple(config.get("capture", {}).get("detect_size", [320, 240])),
        tuning_file=config.get("capture", {}).get("tuning", None),
    )

    app.config["stream_manager"] = StreamManager(
        camera_manager=app.config["camera_manager"]
    )

    app.config["motion_detector"] = MotionDetector(
        camera_manager=app.config["camera_manager"],
        motion_threshold=float(config.get("motion", {}).get("mse_threshold", 7)),
        max_encoding_time=int(config.get("motion", {}).get("motion_gap", 10)),
        notifiers=[logging_notifier, webhook_notifier]
    )

    app.config["status_manager"] = StatusManager(
        camera_manager=app.config["camera_manager"],
        motion_detector=app.config["motion_detector"]
    )

def load_config(config_file=None):
    """Loads configuration from config/config.yml."""
    default_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.default.yml")
    existing_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config/config.yml")

    if not config_file:
        config_file = existing_config_file

    logger = logging.getLogger(__name__)

    if not os.path.exists(config_file):
        if os.path.exists(default_config_file):
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            shutil.copy(default_config_file, config_file)
            logger.info(f"Copied '{default_config_file}' to '{config_file}'")
        else:
            logger.error(f"Default configuration file '{default_config_file}' not found.")
            raise RuntimeError(f"Default configuration file '{default_config_file}' not found.")

    try:
        with open(config_file, 'r') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            if data is None:
                logger.warning(f"Configuration file '{config_file}' is empty. No updates applied.")
                data = {}
            logger.debug(f"Configuration loaded:\n{json.dumps(data, indent=4)}")
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_file}' not found.")
        raise RuntimeError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        raise RuntimeError(f"Error parsing YAML file: {e}")

    return data

def configure_logging(app, config):
    """Configures logging based on application settings."""
    if default_handler in app.logger.handlers:
        app.logger.removeHandler(default_handler)

    log_level = config.get("logging", {}).get("level", "info").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    app.logger.setLevel(numeric_level)
    app.logger.info(f"Logging configured to {log_level} level.")
