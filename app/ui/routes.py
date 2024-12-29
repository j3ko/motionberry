from flask import Blueprint, Response, render_template, current_app, stream_with_context
from app.ui import ui_bp

@ui_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@ui_bp.route('/video_feed')
def video_feed():
    stream_manager = current_app.config["stream_manager"]
    return Response(
        stream_with_context(stream_manager.generate_frames()), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )