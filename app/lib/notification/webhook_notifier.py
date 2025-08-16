import os
import base64
import logging
import threading
import requests
from string import Template
from .event_notifier import EventNotifier

class WebhookNotifier(EventNotifier):
    def __init__(self, config: dict):
        self.logger = logging.getLogger(__name__)
        self.config = config

    def notify(self, action: str, data: dict) -> None:
        if not self.config or action not in self.config:
            return

        actions = self.config[action]

        # Backward compatibility: single webhook_url
        if isinstance(actions, dict) and "webhook_url" in actions:
            actions = [{"type": "http_post", "url": actions["webhook_url"]}]

        if data and data.get("preview_jpeg"):
            data["preview_base64"] = base64.b64encode(data["preview_jpeg"]).decode("ascii")

        for action_def in actions:
            thread = threading.Thread(
                target=self._dispatch_action,
                args=(action_def, data),
                daemon=True,
            )
            thread.start()

    def _dispatch_action(self, action_def: dict, context: dict) -> None:
        try:
            action_type = action_def.get("type")

            action_def = self._substitute_fields(action_def, context)

            if action_type == "http_post":
                self._post_http(action_def["url"], action_def.get("headers", {}), action_def.get("body", ""))
            elif action_type == "form_post":
                self._post_form(action_def["url"], action_def.get("data", {}))
            elif action_type == "json_post":
                self._post_json(action_def["url"], action_def.get("json", {}))
            else:
                self.logger.warning(f"Unknown notification type: {action_type}")
        except Exception as e:
            self.logger.error(f"Failed to dispatch notification: {e}")

    def _post_http(self, url, headers, body):
        try:
            requests.post(url, headers=headers, data=body, timeout=10)
        except Exception as e:
            self.logger.error(f"HTTP POST failed to {url}: {e}")

    def _post_form(self, url, data):
        try:
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            self.logger.error(f"Form POST failed to {url}: {e}")

    def _post_json(self, url, json_data):
        try:
            requests.post(url, json=json_data, timeout=10)
        except Exception as e:
            self.logger.error(f"JSON POST failed to {url}: {e}")

    def _substitute_fields(self, data, context):
        if context is None:
            context = {}

        full_context = {**os.environ, **context}

        if isinstance(data, str):
            return Template(data).safe_substitute(full_context)
        elif isinstance(data, dict):
            return {k: self._substitute_fields(v, full_context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_fields(v, full_context) for v in data]
        return data


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
                    "filename": {"type": "string", "example": "motion_2025-01-06_00-06-23.mkv"},
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