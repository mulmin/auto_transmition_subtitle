import os
import whisper
import srt
from datetime import timedelta
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip

app = Flask(__name__)

# --- 설정 ---
# 업로드 폴더 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 모델 크기 설정 (컴퓨터 성능에 따라 base, small, medium 선택)
MODEL_SIZE = "base"

# 🚀 서버 켤 때 Whisper 모델 미리 로드 (시간 절약)
print(f"⏳ Whisper '{MODEL_SIZE}' 모델을 로딩 중입니다... (잠시만 기다려주세요)")
try:
    WHISPER_MODEL = whisper.load_model(MODEL_SIZE)
    print("✅ 모델 로드 완료!")
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")

# --- 오디오 추출 함수 ---
def extract_audio(video_path):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_temp.mp3")
    
    # MoviePy로 변환
    video_clip = VideoFileClip(video_path)
    video_clip.audio.write_audiofile(audio_path, codec='mp3', logger=None)
    video_clip.close()
    return audio_path

# --- AI 자막 생성 함수 ---
def generate_srt_logic(audio_path):
    # Whisper로 트랜스크립션 수행
    result = WHISPER_MODEL.transcribe(audio_path, language="en", word_timestamps=True)

    subtitles = []
    for i, segment in enumerate(result["segments"]):
        start = timedelta(seconds=segment['start'])
        end = timedelta(seconds=segment['end'])
        text = segment['text'].strip()
        subtitles.append(srt.Subtitle(index=i+1, start=start, end=end, content=text))

    # SRT 파일 저장
    base_name = os.path.splitext(os.path.basename(audio_path))[0].replace('_temp', '')
    srt_filename = f"{base_name}.srt"
    srt_path = os.path.join(UPLOAD_FOLDER, srt_filename)

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt.compose(subtitles))
    
    return srt_path

# --- 웹 라우팅 ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video_file' not in request.files:
            return '파일이 없습니다.'
        
        file = request.files['video_file']
        if file.filename == '':
            return '파일을 선택해주세요.'

        if file:
            filename = secure_filename(file.filename)
            video_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(video_path)

            audio_path = None
            try:
                # 1. 오디오 추출
                audio_path = extract_audio(video_path)
                
                # 2. AI 자막 생성
                srt_path = generate_srt_logic(audio_path)

                # 3. 다운로드 제공
                return send_file(srt_path, as_attachment=True)

            except Exception as e:
                return f"❌ 에러 발생: {str(e)}"
            finally:
                # 청소: 원본 영상과 임시 오디오 삭제 (SRT는 다운로드해야 하니 유지)
                if os.path.exists(video_path): os.remove(video_path)
                if audio_path and os.path.exists(audio_path): os.remove(audio_path)

    return render_template('index.html')

if __name__ == '__main__':
    # 로컬 서버 실행 (debug=True로 하면 에러 메시지를 웹에서 볼 수 있음)
    app.run(debug=True, port=5000)