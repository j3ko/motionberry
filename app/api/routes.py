from flask import jsonify, Response, request, send_from_directory, current_app, stream_with_context
from app.api import api_bp
import os
import queue
from ..version import __version__


@api_bp.route("/status", methods=["GET"])
def status():
    """
    Returns the health status of the API.
    ---
    get:
      summary: Check API health status
      description: Returns the current status of the API to indicate whether it is operational.
      tags: ["Incoming"]
      responses:
        200:
          description: API is operational.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: "ok"
    """
    return jsonify({"status": "ok"})


@api_bp.route('/status_stream')
def status_stream():
    """
    Streams real-time status updates as server-sent events.
    ---
    get:
      summary: Real-time status updates
      description: Streams real-time system status as server-sent events.
      tags: ["Incoming"]
      responses:
        200:
          description: Stream of status events.
          content:
            text/event-stream:
              schema:
                type: string
    """
    status_manager = current_app.config["status_manager"]
    return Response(stream_with_context(status_manager.generate_status()), content_type="text/event-stream")


@api_bp.route("/enable_detection", methods=["POST"])
def enable_detection():
    """
    Enables motion detection.
    ---
    post:
      summary: Enable motion detection
      description: Starts the motion detection process.
      tags: ["Incoming"]
      responses:
        200:
          description: Motion detection started successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
        500:
          description: Error enabling motion detection.
    """
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
def disable_detection():
    """
    Disables motion detection.
    ---
    post:
      summary: Disable motion detection
      description: Stops the motion detection process.
      tags: ["Incoming"]
      responses:
        200:
          description: Motion detection stopped successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
        500:
          description: Error disabling motion detection.
    """
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
    """
    Lists all captured files.
    ---
    get:
      summary: List captured files
      description: Retrieves a list of all captured files in the output directory.
      tags: ["Incoming"]
      responses:
        200:
          description: List of captures.
          content:
            application/json:
              schema:
                type: object
                properties:
                  captures:
                    type: array
                    items:
                      type: string
        500:
          description: Error listing captures.
    """
    file_manager = current_app.config["file_manager"]
    try:
        files = os.listdir(file_manager.output_dir)
        return jsonify({"captures": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/captures/<path:input_path>", methods=["GET"])
def download_capture(input_path):
    """
    Downloads a specific captured file.
    ---
    get:
      summary: Download a captured file
      description: Downloads a specific file from the output directory.
      tags: ["Incoming"]
      parameters:
        - in: path
          name: input_path
          required: true
          schema:
            type: string
          description: Path or filename of the capture to download.
      responses:
        200:
          description: File downloaded successfully.
          content:
            application/octet-stream: {}
        500:
          description: Error downloading file.
    """
    file_manager = current_app.config["file_manager"]
    output_dir = file_manager.output_dir.resolve()

    try:
        resolved_path = (output_dir / input_path).resolve()

        if not resolved_path.is_relative_to(output_dir):
            raise ValueError("Invalid path: Outside allowed directory")

        safe_relative_path = resolved_path.relative_to(output_dir)

        return send_from_directory(output_dir, str(safe_relative_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/snapshot', methods=['POST'])
def take_snapshot():
    """
    Takes a snapshot using the camera.
    ---
    post:
      summary: Take a snapshot
      description: Captures a still image using the camera.
      tags: ["Incoming"]
      responses:
        200:
          description: Snapshot taken successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  filename:
                    type: string
        500:
          description: Error taking snapshot.
    """
    camera_manager = current_app.config["camera_manager"]
    try:
        full_path = camera_manager.take_snapshot()
        return jsonify({"message": "Snapshot taken.", "filename": str(full_path)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/record', methods=['POST'])
def record():
    """
    Records a video for a specified duration.
    ---
    post:
      summary: Record a video
      description: Starts a video recording for a given duration.
      tags: ["Incoming"]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                duration:
                  type: integer
                  description: Recording duration in seconds.
                  example: 10
      responses:
        200:
          description: Video recorded successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  filename:
                    type: string
        400:
          description: Invalid input data.
        500:
          description: Error during recording.
    """
    duration = request.json.get('duration', 0)
    if duration <= 0:
        return jsonify({"error": "Invalid duration"}), 400

    result_queue = queue.Queue()

    camera_manager = current_app.config["camera_manager"]
    camera_manager.record_for_duration(duration, result_queue)

    try:
        full_path = result_queue.get()
        if full_path:
            return jsonify({"filename": str(full_path.name)})
        else:
            return jsonify({"error": "Recording failed or another recording is already in progress"}), 500
    except queue.Empty:
        return jsonify({"error": "Recording timed out"}), 500
