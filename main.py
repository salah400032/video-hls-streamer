# main.py

import streamlit as st
import hashlib
import os
import subprocess

st.set_page_config(page_title="🎞️ HLS Streamer", layout="centered")

HLS_FOLDER = "hls"
ORIGINAL_FOLDER = "originals"
os.makedirs(HLS_FOLDER, exist_ok=True)
os.makedirs(ORIGINAL_FOLDER, exist_ok=True)

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()

st.title("🎞️ تحويل فيديو إلى بث HLS")

video_url = st.text_input("🎥 أدخل رابط الفيديو (يدعم المباشر أو الملفات):")

if st.button("ابدأ التحويل"):
    if not video_url:
        st.warning("❌ الرجاء إدخال رابط الفيديو.")
    else:
        sid = generate_id(video_url)
        out_folder = os.path.join(HLS_FOLDER, sid)
        out_m3u8 = os.path.join(out_folder, "index.m3u8")
        os.makedirs(out_folder, exist_ok=True)
        original_path = os.path.join(ORIGINAL_FOLDER, f"{sid}.mkv")

        # تحميل الفيديو الأصلي
        if not os.path.exists(original_path):
            st.info("⏳ جاري تحميل الفيديو...")
            try:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-headers", f"Referer: {video_url}\r\nUser-Agent: Mozilla/5.0\r\n",
                    "-user_agent", "Mozilla/5.0",
                    "-i", video_url,
                    "-c", "copy",
                    original_path
                ], check=True, timeout=300)
                st.success("📥 تم تحميل الفيديو الأصلي.")
            except Exception as e:
                st.error(f"⚠️ فشل تحميل الفيديو:\n{str(e)}")
                st.stop()
        else:
            st.info("📁 الفيديو الأصلي موجود مسبقًا.")

        # تحويل إلى HLS
        if not os.path.exists(out_m3u8):
            st.info("🔁 جاري التحويل إلى HLS...")
            try:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-protocol_whitelist", "file,http,https,tcp,tls",
                    "-headers", f"User-Agent: Mozilla/5.0\r\nReferer: {video_url}\r\n",
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
                ], check=True, timeout=300)
                st.success("✅ تم التحويل إلى HLS بنجاح!")
            except subprocess.CalledProcessError as e:
                st.error(f"❌ فشل التحويل:\n{e.stderr}")
                st.stop()
            except subprocess.TimeoutExpired:
                st.error("⏱️ انتهى وقت الانتظار. حاول مجددًا.")
                st.stop()
        else:
            st.info("✅ تم العثور على ملف البث مسبقًا.")

        # عرض روابط
        if os.path.exists(out_m3u8):
            st.markdown(f"🎬 [رابط ملف البث (index.m3u8)]({out_m3u8})")
        if os.path.exists(original_path):
            st.markdown(f"⬇️ [تحميل الفيديو الأصلي]({original_path})")
