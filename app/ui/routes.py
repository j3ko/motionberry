from flask import Blueprint, render_template
from app.ui import ui_bp

@ui_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")
