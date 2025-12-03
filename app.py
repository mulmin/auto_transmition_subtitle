import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 팀원(친구)들이 만든 모듈 가져오기
try:
    from audio import AudioExtractor
    from engsrt import WhisperTranscriber
    from en_to_ko import DeepLTranslator
except ImportError as e:
    print(f"❌ 오류: 모듈을 찾을 수 없습니다. ({e})")
    print("👉 audio.py, engsrt.py 등이 app.py와 같은 폴더에 있는지 확인해주세요!")

app = Flask(__name__)
load_dotenv() # .env 파일 로드

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 모델 크기 (친구 코드 설정에 맞춤)
MODEL_SIZE = "small" 

print("⚙️ [초기화] AI 모델 및 번역기 준비 중...")
extractor = AudioExtractor(BASE_DIR) # 친구 코드는 프로젝트 경로를 받음
transcriber = WhisperTranscriber(model_size=MODEL_SIZE)
translator = DeepLTranslator()
print("✅ 시스템 준비 완료!")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video_file' not in request.files: return '파일 없음'
        file = request.files['video_file']
        if file.filename == '': return '선택 안함'

        if file:
            filename = secure_filename(file.filename)
            video_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(video_path)

            audio_path = None
            try:
                # 1. 오디오 추출 (audio.py)
                # 친구 코드는 저장 경로를 내부에서 정하므로 video_path만 넘김
                audio_path = extractor.extract(video_path)
                
                # 2. Whisper 자막 생성 (engsrt.py)
                segments = transcriber.run_whisper(audio_path)
                eng_subtitles = transcriber.create_srt_content(segments)
                
                # 영어 자막 저장
                base_name = os.path.splitext(filename)[0]
                eng_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_en.srt")
                transcriber.save_srt_file(eng_subtitles, eng_srt_path)

                final_download_path = eng_srt_path

                # 3. 한글 번역 (en_to_ko.py)
                if translator.translator:
                    print("[INFO] DeepL 번역 시작...")
                    kor_subtitles = transcriber.translate_subtitles(eng_subtitles, translator)
                    
                    kor_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_ko.srt")
                    transcriber.save_srt_file(kor_subtitles, kor_srt_path)
                    final_download_path = kor_srt_path
                
                return send_file(final_download_path, as_attachment=True)

            except Exception as e:
                return f"❌ 에러 발생: {str(e)}"
            finally:
                # 청소
                if os.path.exists(video_path): os.remove(video_path)
                if audio_path and os.path.exists(audio_path): 
                    try: os.remove(audio_path)
                    except: pass

    return render_template('index.html')

if __name__ == '__main__':
    # 5000번 포트 충돌 방지를 위해 5001번으로 실행
    app.run(debug=True, port=5001)