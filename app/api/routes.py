from flask import Blueprint, jsonify, Response, send_from_directory, current_app, stream_with_context
from app.api import api_bp
import os

@api_bp.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok"})

@api_bp.route('/status_stream')
def status_stream():
    status_manager = current_app.config["status_manager"]
    return Response(stream_with_context(status_manager.generate_status()), content_type="text/event-stream")

@api_bp.route("/enable_detection", methods=["POST"])
def start_motion_detection():
    motion_detector = current_app.config["motion_detector"]
    try:
        if not motion_detector.is_running:
            motion_detector.start()
            return jsonify({"status": "Motion detection started."})
        else:
            return jsonify({"status": "Motion detection is already running."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@api_bp.route("/disable_detection", methods=["POST"])
def stop_motion_detection():
    motion_detector = current_app.config["motion_detector"]
    try:
        if motion_detector.is_running:
            motion_detector.stop()
            return jsonify({"status": "Motion detection stopped."})
        else:
            return jsonify({"status": "Motion detection is not running."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/captures", methods=["GET"])
def list_captures():
    file_manager = current_app.config["file_manager"]
    try:
        files = os.listdir(file_manager.output_dir)
        return jsonify({"captures": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/captures/<filename>", methods=["GET"])
def download_capture(filename):
    file_manager = current_app.config["file_manager"]
    try:
        return send_from_directory(file_manager.output_dir, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api_bp.route('/snapshot', methods=['POST'])
def take_snapshot():
    camera_manager = current_app.config["camera_manager"]
    try:
        filename = camera_manager.take_snapshot()
        return jsonify({"message": "Snapshot taken.", "filename": str(filename)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500