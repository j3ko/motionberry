from flask import Blueprint, jsonify, request, send_from_directory, current_app
from app.api import api_bp
import os

@api_bp.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok"})

@api_bp.route("/start", methods=["POST"])
def start_motion_detection():
    motion_detector = current_app.config["motion_detector"]
    if not motion_detector.is_running:
        motion_detector.start()
        return jsonify({"status": "Motion detection started."})
    else:
        return jsonify({"status": "Motion detection is already running."})

@api_bp.route("/stop", methods=["POST"])
def stop_motion_detection():
    motion_detector = current_app.config["motion_detector"]
    if motion_detector.is_running:
        motion_detector.stop()
        return jsonify({"status": "Motion detection stopped."})
    else:
        return jsonify({"status": "Motion detection is not running."})

@api_bp.route("/recordings", methods=["GET"])
def list_recordings():
    motion_detector = current_app.config["motion_detector"]
    files = os.listdir(motion_detector.video_dir)
    return jsonify({"recordings": files})

@api_bp.route("/recordings/<filename>", methods=["GET"])
def download_recording(filename):
    motion_detector = current_app.config["motion_detector"]
    return send_from_directory(motion_detector.video_dir, filename)