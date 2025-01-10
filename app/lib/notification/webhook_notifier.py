import logging
import threading
import requests
from .notifier import Notifier

class WebhookNotifier(Notifier):
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config

    def notify(self, action: str, data: dict) -> None:
        if not self.config:
            return

        if action in self.config and "webhook_url" in self.config[action]:
            thread = threading.Thread(
                target=self._post, 
                args=(self.config[action]["webhook_url"], data),
                daemon=True,
            )
            thread.start()

    def _post(self, url, data: dict) -> None:
        try:
            response = requests.post(url, json=data, timeout=10)
        except Exception as e:
            self.logger.error(f"Unable to connect to {url}: {e}")


def get_webhook_specs():
    webhook_definitions = [
        {"path": "/application_started"},
        {"path": "/detection_enabled"},
        {"path": "/detection_disabled"},
        {"path": "/motion_started"},
        {
            "path": "/motion_stopped",
            "payload_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "example": "motion_2025-01-06_00-06-23.mp4"},
                },
                "required": ["filename"],
            },
        },
    ]
    return [generate_webhook_spec(**webhook) for webhook in webhook_definitions]

def generate_webhook_spec(path, payload_schema=None):
    """
    Generate a webhook spec for OpenAPI 3.0.

    Args:
        path (str): The webhook path (e.g., "/motion_detected").
        payload_schema (dict, optional): The schema for the request payload, if applicable.

    Returns:
        dict: A dictionary representing the OpenAPI spec for the given webhook.
    """
    webhook_spec = {
        "post": {
            "summary": f"Webhook for {path.strip('/')}",
            "description": f"Triggered by the {path.strip('/')} event.",
            "tags": ["Outgoing"],
            "responses": {
                "200": {
                    "description": "Success"
                }
            }
        }
    }

    if payload_schema:
        webhook_spec["post"]["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": payload_schema
                }
            }
        }

    return {path: webhook_spec}