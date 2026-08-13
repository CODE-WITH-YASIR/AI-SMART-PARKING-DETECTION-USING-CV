```python
import os
import uuid
import logging
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    abort,
)
from werkzeug.utils import secure_filename

from detection import process_image, process_video, TOTAL_SLOTS


# ============================================================
# APP CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
OUTPUT_FOLDER = BASE_DIR / "static" / "outputs"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


# Supported file formats
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "bmp"}
ALLOWED_VIDEO_EXT = {"mp4", "avi", "mov", "mkv"}

# Maximum upload size: 300 MB
MAX_UPLOAD_SIZE = 300 * 1024 * 1024


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

# Use environment variable when available.
# For local development, fallback value is used.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smart-parking-development-secret"
)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["OUTPUT_FOLDER"] = str(OUTPUT_FOLDER)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def allowed_file(filename, allowed_extensions):
    """Check whether a filename has an allowed extension."""
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed_extensions


def generate_safe_filename(original_filename):
    """Generate a unique and safe filename."""
    safe_name = secure_filename(original_filename)

    if not safe_name:
        safe_name = "uploaded_file"

    unique_id = uuid.uuid4().hex[:8]

    return f"{unique_id}_{safe_name}"


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle files larger than MAX_CONTENT_LENGTH."""
    flash("File is too large. Maximum allowed size is 300 MB.")
    return redirect(url_for("home"))


@app.errorhandler(404)
def page_not_found(error):
    """Handle invalid routes."""
    return render_template(
        "index.html",
        total_slots=TOTAL_SLOTS,
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    """Handle unexpected server errors."""
    logger.exception("Internal server error")
    flash("Something went wrong while processing your request.")
    return redirect(url_for("home"))


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    """
    Health endpoint for deployment platforms such as Render.
    """
    return {
        "status": "healthy",
        "service": "AI Smart Parking Detection",
        "total_slots": TOTAL_SLOTS,
    }, 200


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():
    """Render the Smart Parking Detection dashboard."""
    return render_template(
        "index.html",
        total_slots=TOTAL_SLOTS,
    )


# ============================================================
# IMAGE DETECTION
# ============================================================

@app.route("/detect/image", methods=["POST"])
def detect_image():
    """Process an uploaded parking image."""

    file = request.files.get("image_file")

    if not file or not file.filename:
        flash("Please choose an image file to upload.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename, ALLOWED_IMAGE_EXT):
        flash("Unsupported image format. Use JPG, JPEG, PNG or BMP.")
        return redirect(url_for("home"))

    filename = generate_safe_filename(file.filename)
    input_path = UPLOAD_FOLDER / filename

    try:
        file.save(input_path)

        logger.info("Processing image: %s", filename)

        output_name, stats = process_image(
            str(input_path),
            str(OUTPUT_FOLDER),
        )

        logger.info("Image processing completed: %s", output_name)

    except Exception:
        logger.exception("Image detection failed")

        # Remove failed upload if possible
        try:
            if input_path.exists():
                input_path.unlink()
        except OSError:
            pass

        flash("Image detection failed. Please try another image.")
        return redirect(url_for("home"))

    return render_template(
        "result_image.html",
        result_file=output_name,
        stats=stats,
    )


# ============================================================
# VIDEO DETECTION
# ============================================================

@app.route("/detect/video", methods=["POST"])
def detect_video():
    """Process an uploaded parking video."""

    file = request.files.get("video_file")

    if not file or not file.filename:
        flash("Please choose a video file to upload.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
        flash("Unsupported video format. Use MP4, AVI, MOV or MKV.")
        return redirect(url_for("home"))

    filename = generate_safe_filename(file.filename)
    input_path = UPLOAD_FOLDER / filename

    try:
        file.save(input_path)

        logger.info("Processing video: %s", filename)

        output_name, stats = process_video(
            str(input_path),
            str(OUTPUT_FOLDER),
        )

        logger.info("Video processing completed: %s", output_name)

    except Exception:
        logger.exception("Video detection failed")

        try:
            if input_path.exists():
                input_path.unlink()
        except OSError:
            pass

        flash("Video detection failed. Please try another video.")
        return redirect(url_for("home"))

    return render_template(
        "result_video.html",
        result_file=output_name,
        stats=stats,
    )


# ============================================================
# SERVE PROCESSED OUTPUTS
# ============================================================

@app.route("/outputs/<path:filename>")
def serve_output(filename):
    """Serve processed detection results."""
    return send_from_directory(
        str(OUTPUT_FOLDER),
        filename,
    )


# ============================================================
# DOWNLOAD RESULTS
# ============================================================

@app.route("/download/<path:filename>")
def download(filename):
    """Download a processed result file."""

    file_path = OUTPUT_FOLDER / filename

    if not file_path.exists() or not file_path.is_file():
        abort(404)

    return send_from_directory(
        str(OUTPUT_FOLDER),
        filename,
        as_attachment=True,
    )


# ============================================================
# APPLICATION STARTUP
# ============================================================

if __name__ == "__main__":
    # Render provides PORT through environment variables.
    # Local development falls back to port 10000.

    port = int(os.environ.get("PORT", 10000))

    logger.info(
        "Starting AI Smart Parking Detection on port %s",
        port,
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        threaded=True,
    )
```
