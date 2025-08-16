from flask import Blueprint, request, Response, render_template, current_app, stream_with_context
from app.ui import ui_bp
from app.version import __version__

@ui_bp.app_context_processor
def inject_version():
    return {"version": __version__}

@ui_bp.route("/", methods=["GET"])
def index():
    stream = request.args.get('stream', 'main')
    return render_template("index.html", stream=stream)

@ui_bp.route('/video_feed')
def video_feed():
    stream = request.args.get('stream', 'main')
    stream_manager = current_app.config["stream_manager"]
    return Response(
        stream_with_context(stream_manager.generate_frames(stream)), 
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )