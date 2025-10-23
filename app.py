import os
import subprocess
from flask import Flask, request, render_template, send_from_directory
import hashlib
import threading

app = Flask(__name__)
HLS_FOLDER = "hls_streams"
os.makedirs(HLS_FOLDER, exist_ok=True)

def generate_hls(url, stream_id):
    stream_path = os.path.join(HLS_FOLDER, stream_id)
    os.makedirs(stream_path, exist_ok=True)
    hls_file = os.path.join(stream_path, "index.m3u8")

    if not os.path.exists(hls_file):
        cmd = [
            "ffmpeg", "-i", url,
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac",
            "-threads", "0",                   # usa todos os cores
            "-f", "hls",
            "-hls_time", "60",
            "-hls_list_size", "60",
            "-hls_flags", "independent_segments",
            hls_file
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_channels():
    channels = []
    if not os.path.exists("playlist.m3u"):
        return channels

    with open("playlist.m3u", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            info = line
            url = ""
            # Skip empty lines to find next URL
            j = i + 1
            while j < len(lines) and lines[j].startswith("#"):
                j += 1
            if j < len(lines):
                url = lines[j]
            
            name = info.split(",")[-1].strip()
            
            # Extract tags safely
            def get_tag(tag):
                if f'{tag}="' in info:
                    return info.split(f'{tag}="')[1].split('"')[0]
                return ""
            
            channels.append({
                "name": name,
                "url": url,
                "tvg-name": get_tag("tvg-name"),
                "tvg-id": get_tag("tvg-id"),
                "tvg-logo": get_tag("tvg-logo"),
                "group-title": get_tag("group-title") or "No Group"
            })
            i = j  # jump past the URL
        else:
            i += 1
    return channels



@app.route('/')
def index():
    channels = load_channels()
    return render_template("index.html", channels=channels)


@app.route('/watch')
def watch():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400

    stream_id = hashlib.md5(url.encode()).hexdigest()[:10]

    # roda em thread para não bloquear
    threading.Thread(target=generate_hls, args=(url, stream_id), daemon=True).start()

    # renderiza HTML imediatamente
    return render_template("watch.html", stream_id=stream_id)


@app.route('/hls/<stream_id>/<path:filename>')
def hls(stream_id, filename):
    folder = os.path.abspath(os.path.join(HLS_FOLDER, stream_id))
    return send_from_directory(folder, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
