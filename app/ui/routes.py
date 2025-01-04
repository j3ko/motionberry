from flask import Blueprint, Response, render_template, current_app, stream_with_context
from app.ui import ui_bp
from app.version import __version__
import os

@ui_bp.app_context_processor
def inject_version():
    return {"version": __version__}

@ui_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# @ui_bp.route('/video_feed')
# def video_feed():
#     stream_manager = current_app.config["stream_manager"]
#     return Response(
#         stream_with_context(stream_manager.generate_frames()), 
#         mimetype='multipart/x-mixed-replace; boundary=frame'
#     )

@ui_bp.route('/video_feed')
def video_feed():
    # Path to the static JPEG file
    static_image_path = os.path.join(current_app.root_path, 'static', 'backyard.jpeg')
    
    def generate_static_frame():
        with open(static_image_path, 'rb') as image_file:
            frame = image_file.read()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    return Response(
        stream_with_context(generate_static_frame()),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )