import os
import subprocess
from flask import Flask, request, render_template, send_from_directory
import time


app = Flask(__name__)
HLS_FOLDER = "hls_streams"
os.makedirs(HLS_FOLDER, exist_ok=True)

# setup the files folder


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/watch')
def watch():
    url = request.args.get("url")
    if not url:
        return "Missing URL", 400

    # gera um id simples
    stream_id = str(abs(hash(url)))[:10]
    stream_path = os.path.join(HLS_FOLDER, stream_id)
    os.makedirs(stream_path, exist_ok=True)

    # FFmpeg: gera HLS (.m3u8 + .ts)
    hls_file = os.path.join(stream_path, "index.m3u8")
    if not os.path.exists(hls_file):
        cmd = [
            "ffmpeg", "-i", url,
            "-c", "copy", "-f", "hls",
            "-hls_time", "4", "-hls_list_size", "5",
            "-hls_flags", "delete_segments",
            hls_file
        ]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # espera 1-2 segundos para gerar o arquivo inicial
        timeout = 10
        while not os.path.exists(hls_file) and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5

    # renderiza HTML com a URL do HLS
    return render_template("watch.html", stream_id=stream_id)

@app.route('/hls/<stream_id>/<path:filename>')
def hls(stream_id, filename):
    folder = os.path.abspath(os.path.join(HLS_FOLDER, stream_id))
    return send_from_directory(folder, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
