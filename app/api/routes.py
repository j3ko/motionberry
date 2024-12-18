from flask import Blueprint, jsonify, request, send_from_directory, current_app
from app.api import api_bp
import os

@api_bp.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok"})

@api_bp.route("/start_motion", methods=["POST"])
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
        
@api_bp.route("/stop_motion", methods=["POST"])
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

@api_bp.route("/recordings", methods=["GET"])
def list_recordings():
    motion_detector = current_app.config["motion_detector"]
    try:
        files = os.listdir(motion_detector.video_dir)
        return jsonify({"recordings": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/recordings/<filename>", methods=["GET"])
def download_recording(filename):
    motion_detector = current_app.config["motion_detector"]
    try:
        return send_from_directory(motion_detector.video_dir, filename)
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