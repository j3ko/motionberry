import logging
import os
import json
from flask import Flask
from .api import api_bp
from .ui import ui_bp
from .version import __version__
from .config_watcher import start_config_watcher
from .utils import load_config, configure_logging, initialize_components, config_lock

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

    # Load initial configuration
    config = load_config(config_file)
    with config_lock:
        app.config.update(config)
        configure_logging(app, config)
        initialize_components(app, config)

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)

    if app.config.get("env", "prod") == "dev":
        register_openapi_spec(app, "docs/openapi.json")

    # Start the config file watcher
    start_config_watcher(app, config_file or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config/config.yml"))

    app.logger.info("Application initialized successfully.")
    return app

def register_openapi_spec(app, file_path):
    """Registers API routes and generates the OpenAPI spec."""
    from apispec import APISpec
    from apispec.ext.marshmallow import MarshmallowPlugin
    from apispec_webframeworks.flask import FlaskPlugin
    from .api.routes import status, enable_detection, disable_detection, list_captures, download_capture, take_snapshot, record
    from .lib.notification.webhook_notifier import get_webhook_specs

    spec = APISpec(
        title="Motionberry API",
        version=__version__,
        openapi_version="3.0.3",
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
    )
    webhook_specs = get_webhook_specs()

    with app.app_context():
        spec.path(view=status)
        spec.path(view=enable_detection)
        spec.path(view=disable_detection)
        spec.path(view=list_captures)
        spec.path(view=download_capture)
        spec.path(view=take_snapshot)
        spec.path(view=record)

        for webhook_spec in webhook_specs:
            for path, definition in webhook_spec.items():
                spec._paths[path] = definition

        with open(file_path, "w") as f:
            json.dump(spec.to_dict(), f, indent=2)
        print("OpenAPI spec written to openapi.json")