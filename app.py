# app.py
import os
import glob
import subprocess
import zipfile
import time
from flask import Flask, send_file, jsonify, render_template

app = Flask(__name__, template_folder="templates")

SCRAPER_SCRIPT = "igod_scraper.py"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def latest_progress_tail(nlines=40):
    """Return last nlines of the most recent progress file in DATA_DIR."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*_IGOD_progress.txt")), reverse=True)
    if not files:
        return ""
    latest = files[0]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-nlines:])
    except Exception:
        return ""

@app.route("/status")
def status():
    """Return last lines of the latest progress file as JSON."""
    return jsonify({"progress": latest_progress_tail(40)})

def run_scraper():
    """Run igod_scraper.py as a subprocess."""
    proc = subprocess.run(["python3", SCRAPER_SCRIPT], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr

def make_zip():
    """ZIP only the CSV files from data/ and return the ZIP path."""
    timestamp = int(time.time())
    zip_path = f"/tmp/igod_outputs_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for fname in os.listdir(DATA_DIR):
            if fname.lower().endswith(".csv"):
                z.write(os.path.join(DATA_DIR, fname), arcname=fname)
    return zip_path

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/download")
def download():
    code, out, err = run_scraper()
    if code != 0:
        # Return error details for debugging
        return jsonify({"returncode": code, "status": "error", "stderr": err}), 500

    zip_path = make_zip()
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name="district_data.zip")
    return jsonify({"status": "no output"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
