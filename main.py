from flask import Flask, request, send_from_directory
import os, subprocess, hashlib

app = Flask(name)
HLS_FOLDER = "hls"
ORIGINAL_FOLDER = "originals"
os.makedirs(HLS_FOLDER, exist_ok=True)
os.makedirs(ORIGINAL_FOLDER, exist_ok=True)

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()

@app.route('/', methods=['GET'])
def home():
    return '''
    <form method="POST" action="/process">
        <input type="text" name="video_url" placeholder="ضع رابط الفيديو هنا" style="width:300px;">
        <button type="submit">تحويل إلى HLS</button>
    </form>
    '''

@app.route('/process', methods=['POST'])
def process_video():
    video_url = request.form.get("video_url")
    if not video_url:
        return "❌ رابط الفيديو مفقود", 400

    sid = generate_id(video_url)
    out_folder = os.path.join(HLS_FOLDER, sid)
    out_m3u8 = os.path.join(out_folder, "index.m3u8")
    os.makedirs(out_folder, exist_ok=True)

    original_path = os.path.join(ORIGINAL_FOLDER, f"{sid}.mkv")

    result_html = ""

    # تنزيل الملف الأصلي إن لم يكن موجودًا
    if not os.path.exists(original_path):
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-headers", f"Referer: {video_url}\r\nUser-Agent: Mozilla/5.0\r\n",
                "-user_agent", "Mozilla/5.0",
                "-i", video_url,
                "-c", "copy",
                original_path
            ], check=True, timeout=300, capture_output=True, text=True)
            result_html += f"📥 تم حفظ الفيديو الأصلي<br><a href=\"/download/{sid}\" target=\"_blank\">⬇️ تحميل الفيديو الأصلي</a><br><br>"
        except Exception as e:
            result_html += f"⚠️ فشل حفظ الفيديو الأصلي: {str(e)}<br>"

    else:
        result_html += f"📁 الفيديو الأصلي موجود مسبقًا<br><a href=\"/download/{sid}\" target=\"_blank\">⬇️ تحميل الفيديو الأصلي</a><br><br>"

    # تحويل إلى HLS إن لم يكن موجودًا
    if not os.path.exists(out_m3u8):
        headers = (
            "User-Agent: Mozilla/5.0\r\n"
            f"Referer: {video_url}\r\n"
        )

        cmd = [
            "ffmpeg", "-y",
            "-protocol_whitelist", "file,http,https,tcp,tls",
            "-headers", headers,
            "-user_agent", "Mozilla/5.0",
            "-i", video_url,
            "-map", "0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-f", "hls",
            "-hls_time", "10",
            "-hls_list_size", "0",
            "-hls_segment_filename", os.path.join(out_folder, "segment_%03d.ts"),
            out_m3u8
        ]

        try:
            subprocess.run(cmd, check=True, timeout=300, capture_output=True, text=True)
            result_html += f"✅ تم التحويل إلى HLS بنجاح<br><a href=\"/hls/{sid}/index.m3u8\" target=\"_blank\">رابط البث</a>"
        except subprocess.CalledProcessError as e:
            return f"""❌ خطأ أثناء التحويل (كود {e.returncode}):<br><pre>{e.stderr}</pre>""", 500
        except subprocess.TimeoutExpired:
            return "⏱️ انتهى وقت الانتظار. حاول لاحقًا أو برابط أخف.", 504
    else:
        result_html += f"✅ البث موجود مسبقًا<br><a href=\"/hls/{sid}/index.m3u8\" target=\"_blank\">رابط البث</a>"

    return result_html

@app.route('/hls/<sid>/<filename>')
def serve_segment(sid, filename):
    return send_from_directory(os.path.join(HLS_FOLDER, sid), filename)

@app.route('/download/<sid>')
def download_original(sid):
    path = os.path.join(ORIGINAL_FOLDER, f"{sid}.mkv")
    if os.path.exists(path):
        return send_from_directory(ORIGINAL_FOLDER, f"{sid}.mkv", as_attachment=True)
    return "❌ الملف غير موجود", 404

if name == 'main':
    app.run(host="0.0.0.0", port=3001, debug=True)
