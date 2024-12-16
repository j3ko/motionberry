# app/ui/__init__.py
from flask import Blueprint

ui_bp = Blueprint("ui", __name__)

from app.ui import routes