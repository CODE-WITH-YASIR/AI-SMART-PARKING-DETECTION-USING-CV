import os
import uuid
import time
import cv2

from util import get_parking_spots_bboxes, empty_or_not, EMPTY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASK_PATH = os.path.join(BASE_DIR, "mask_1920_1080.png")

# Parking slot boxes are computed once at startup from the mask
# (same mask used in the notebook — do not regenerate/retrain).
PARKING_SPOTS = get_parking_spots_bboxes(MASK_PATH)
TOTAL_SLOTS = len(PARKING_SPOTS)


def _draw_and_count(frame):
    """
    Runs empty_or_not() on every parking spot in a single frame,
    draws green/red boxes, and returns (annotated_frame, free_count).
    Mirrors the notebook's per-frame loop exactly.
    """
    free_spaces = 0

    for (x, y, w, h) in PARKING_SPOTS:
        crop = frame[y:y + h, x:x + w]

        if crop.size == 0:
            continue

        status = empty_or_not(crop)

        if status == EMPTY:
            color = (0, 255, 0)  # green
            free_spaces += 1
        else:
            color = (0, 0, 255)  # red

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    return frame, free_spaces


def _overlay_stats(frame, free_spaces, total_slots):
    occupied = total_slots - free_spaces
    occ_pct = (occupied / total_slots * 100) if total_slots else 0

    label = f"Free: {free_spaces}/{total_slots}  |  Occupied: {occupied}  |  Occupancy: {occ_pct:.1f}%"

    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.rectangle(frame, (0, 0), (tw + 20, th + 25), (0, 0, 0), -1)
    cv2.putText(frame, label, (10, th + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    return frame


def process_image(input_path, output_dir):
    """
    Detect parking slot occupancy in a single image.
    Returns (output_filename, stats_dict).
    """
    frame = cv2.imread(input_path)
    if frame is None:
        raise ValueError("Could not read the uploaded image.")

    frame, free_spaces = _draw_and_count(frame)
    frame = _overlay_stats(frame, free_spaces, TOTAL_SLOTS)

    occupied = TOTAL_SLOTS - free_spaces
    occ_pct = round((occupied / TOTAL_SLOTS * 100), 1) if TOTAL_SLOTS else 0

    out_name = f"result_{uuid.uuid4().hex[:8]}.jpg"
    out_path = os.path.join(output_dir, out_name)
    cv2.imwrite(out_path, frame)

    stats = {
        "total": TOTAL_SLOTS,
        "free": free_spaces,
        "occupied": occupied,
        "occupancy_pct": occ_pct,
    }
    return out_name, stats


def process_video(input_path, output_dir):
    """
    Detect parking slot occupancy across an entire video and write
    an annotated copy, exactly like the notebook's "smart_parking_output.mp4"
    export cell. Stats reported are taken from the final processed frame.
    Returns (output_filename, stats_dict).
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError("Could not open the uploaded video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    raw_name = f"result_raw_{uuid.uuid4().hex[:8]}.mp4"
    raw_path = os.path.join(output_dir, raw_name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(raw_path, fourcc, fps, (width, height))

    last_free = 0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        frame, free_spaces = _draw_and_count(frame)
        frame = _overlay_stats(frame, free_spaces, TOTAL_SLOTS)
        out.write(frame)
        last_free = free_spaces

    cap.release()
    out.release()

    # Re-encode to H.264 so it plays back in-browser (same as the
    # notebook's ffmpeg re-encode cell before download).
    final_name = f"result_{uuid.uuid4().hex[:8]}.mp4"
    final_path = os.path.join(output_dir, final_name)
    ffmpeg_cmd = f'ffmpeg -y -i "{raw_path}" -vcodec libx264 -pix_fmt yuv420p "{final_path}" -loglevel error'
    ret_code = os.system(ffmpeg_cmd)

    if ret_code != 0 or not os.path.exists(final_path):
        # ffmpeg unavailable — fall back to the raw mp4v file
        final_name = raw_name
    else:
        os.remove(raw_path)

    occupied = TOTAL_SLOTS - last_free
    occ_pct = round((occupied / TOTAL_SLOTS * 100), 1) if TOTAL_SLOTS else 0

    stats = {
        "total": TOTAL_SLOTS,
        "free": last_free,
        "occupied": occupied,
        "occupancy_pct": occ_pct,
        "frames_processed": frame_count,
    }
    return final_name, stats
