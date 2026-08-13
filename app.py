import os
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_from_directory, abort
)
from werkzeug.utils import secure_filename

from detection import process_image, process_video, TOTAL_SLOTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "bmp"}
ALLOWED_VIDEO_EXT = {"mp4", "avi", "mov", "mkv"}

app = Flask(__name__)
app.secret_key = "smart-parking-secret-key"  # change in production
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB max upload


def allowed_file(filename, allowed_ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


@app.route("/")
def home():
    return render_template("index.html", total_slots=TOTAL_SLOTS)


@app.route("/detect/image", methods=["POST"])
def detect_image():
    file = request.files.get("image_file")

    if not file or file.filename == "":
        flash("Please choose an image file to upload.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename, ALLOWED_IMAGE_EXT):
        flash("Unsupported image format. Use JPG, JPEG, PNG or BMP.")
        return redirect(url_for("home"))

    filename = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    try:
        output_name, stats = process_image(input_path, OUTPUT_FOLDER)
    except Exception as e:
        flash(f"Detection failed: {e}")
        return redirect(url_for("home"))

    return render_template(
        "result_image.html",
        result_file=output_name,
        stats=stats,
    )


@app.route("/detect/video", methods=["POST"])
def detect_video():
    file = request.files.get("video_file")

    if not file or file.filename == "":
        flash("Please choose a video file to upload.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
        flash("Unsupported video format. Use MP4, AVI, MOV or MKV.")
        return redirect(url_for("home"))

    filename = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(input_path)

    try:
        output_name, stats = process_video(input_path, OUTPUT_FOLDER)
    except Exception as e:
        flash(f"Detection failed: {e}")
        return redirect(url_for("home"))

    return render_template(
        "result_video.html",
        result_file=output_name,
        stats=stats,
    )


@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)


@app.route("/download/<path:filename>")
def download(filename):
    if not os.path.exists(os.path.join(OUTPUT_FOLDER, filename)):
        abort(404)
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
