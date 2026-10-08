# AI VisionGuard

Real-time object detection, distance estimation, risk scoring and security event monitoring web application.

## What is included
- YOLO11 object detection
- Real-time webcam dashboard
- Start/Stop controls
- Confidence scores
- Distance estimation using focal-length calibration
- Risk levels: LOW / MEDIUM / HIGH / CRITICAL
- Restricted-zone indicator
- Automatic high-risk event logging in SQLite
- Event snapshots
- CPU/RAM/FPS monitoring
- Settings page
- Responsive dark web dashboard
- Windows quick-start and stop scripts

## Quick Start (Windows)
1. Install Python 3.10-3.13 from python.org and make sure `py` works in Command Prompt.
2. Extract this ZIP to a normal folder.
3. Double-click `start_windows.bat`.
4. The script creates `.venv`, installs dependencies, downloads the YOLO model on first use, and opens the dashboard.
5. Click **START CAMERA**.
6. Allow camera access if Windows asks.
7. Click **STOP CAMERA** when finished.

The first run can take several minutes because Python packages and the YOLO model may need to download.

## Manual start
```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000

## Distance calibration
The application uses:

`distance = real_object_height * focal_length / object_height_in_pixels`

The default focal length is only a starting value. For meaningful physical measurements, place a known object/person at a measured distance, adjust focal length until the dashboard distance matches the measured distance, then save it.

## Camera
The default camera is index 0. Use the Camera field to change the backend camera index before starting.

## Data
- SQLite database: `storage/visionguard.db`
- Event snapshots: `snapshots/`
- Old project source: `OLD_PROJECT.txt`

## Important limitations
This release is designed as a local prototype/portfolio foundation. Monocular distance is an estimate and depends on camera calibration, object size, camera angle and detector bounding-box quality. It is not a safety-certified security system.

## Project structure
- `app/main.py` — FastAPI API, camera worker, YOLO detection, distance/risk logic
- `static/index.html` — dashboard
- `static/style.css` — dashboard styling
- `static/app.js` — frontend API/UI logic
- `requirements.txt` — Python dependencies
- `start_windows.bat` — one-click start
- `stop_windows.bat` — stop helper


## Python 3.14 note

This version is prepared for **regular CPython 3.14 on Windows**, not the free-threaded `3.14t` build. The included `start_windows.bat` explicitly creates `.venv` with `py -3.14` and installs binary wheels only. This avoids the `polars-runtime-32` Rust/Cargo build error. See `README_PYTHON_3_14.txt` for details.
