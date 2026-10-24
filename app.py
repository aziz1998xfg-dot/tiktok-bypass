import os
import uuid
import imageio_ffmpeg
from flask import Flask, render_template, request, send_file, jsonify
from moviepy import VideoFileClip
from moviepy.video import fx as vfx


# إجبار النظام على استخدام النسخة المدمجة من FFmpeg لضمان التوافق محلياً وسحابياً
os.environ["IMAGEIO_FFMPEG_EXE"] = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)

UPLOAD_FOLDER = 'temp_videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_video(video_url, unique_id):
    raw_path = os.path.join(UPLOAD_FOLDER, f"raw_{unique_id}.mp4")
    output_path = os.path.join(UPLOAD_FOLDER, f"remixed_{unique_id}.mp4")
    
    # 1. تنزيل فيديو التيك توك بأعلى جودة
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': raw_path,
        'merge_output_format': 'mp4',
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        
    # 2. هندسة فك بصمة الفيديو الرقمية (Anti-Copyright)
    clip = VideoFileClip(raw_path)
    
    # [بصري] قلب الفيديو أفقياً وتغيير السطوع والتباين لتغيير الـ Hash تماماً
    remixed_clip = clip.fx(vfx.mirror_x)
    remixed_clip = remixed_clip.fx(vfx.colorx, 1.02)
    remixed_clip = remixed_clip.fx(vfx.lum_contrast, lum=2, contract=3)
    
    # [بصري] قص 5% من الحواف لحذف العلامات المائية المخفية والتأطير القديم
    w, h = remixed_clip.size
    remixed_clip = remixed_clip.crop(x1=int(w*0.05), y1=int(h*0.05), x2=int(w*0.95), y2=int(h*0.95))
    
    # [زمني وسمعي] تسريع الفيديو بنسبة 6% لتغيير وتيرة الحركة والتردد الصوتي
    remixed_clip = remixed_clip.fx(vfx.speedx, 1.06)
    
    # 3. تصدير الفيديو وحذف البيانات المخفية القديمة (Metadata)
    remixed_clip.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac",
        threads=4,
        ffmpeg_params=["-map_metadata", "-1"],
        logger=None
    )
    
    # تنظيف وإغلاق الملفات
    clip.close()
    remixed_clip.close()
    if os.path.exists(raw_path):
        os.remove(raw_path)
        
    return output_path

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def handle_video():
    data = request.json
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({'error': 'الرجاء إدخال رابط صحيح'}), 400
        
    try:
        unique_id = str(uuid.uuid4())[:8]
        final_file_path = process_video(video_url, unique_id)
        return jsonify({'download_url': f'/download/{unique_id}'})
    except Exception as e:
        return jsonify({'error': f'حدث خطأ أثناء المعالجة: {str(e)}'}), 500

@app.route('/download/<id>')
def download(id):
    file_path = os.path.join(UPLOAD_FOLDER, f"remixed_{id}.mp4")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name="tiktok_ready.mp4")
    return "الملف غير موجود", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
