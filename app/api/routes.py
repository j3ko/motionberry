from flask import Blueprint, jsonify, Response, request, send_from_directory, current_app, stream_with_context
from app.api import api_bp
from pathlib import Path
import os
import queue

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

@api_bp.route("/captures/<path:input_path>", methods=["GET"])
def download_capture(input_path):
    file_manager = current_app.config["file_manager"]
    
    output_dir_str = str(file_manager.output_dir.resolve())
    input_path = str(Path(input_path).resolve())

    try:
        if output_dir_str in input_path:
            input_path = input_path.replace(output_dir_str, "").lstrip("/").lstrip("\\")
        
        # Check for traversal attacks
        safe_filename = Path(input_path).name

        return send_from_directory(file_manager.output_dir, safe_filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api_bp.route('/snapshot', methods=['POST'])
def take_snapshot():
    camera_manager = current_app.config["camera_manager"]
    try:
        full_path = camera_manager.take_snapshot()
        return jsonify({"message": "Snapshot taken.", "filename": str(full_path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api_bp.route('/record', methods=['POST'])
def record():
    duration = request.json.get('duration', 0)
    if duration <= 0:
        return jsonify({"error": "Invalid duration"}), 400

    result_queue = queue.Queue()

    camera_manager = current_app.config["camera_manager"]
    camera_manager.record_for_duration(duration, result_queue)

    try:
        full_path = result_queue.get()
        if full_path:
            return jsonify({"filename": str(full_path)})
        else:
            return jsonify({"error": "Recording failed or another recording is already in progress"}), 500
    except queue.Empty:
        return jsonify({"error": "Recording timed out"}), 500