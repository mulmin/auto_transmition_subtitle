import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 팀원(친구)들의 모듈 가져오기 (에러 처리 추가)
try:
    from audio import AudioExtractor
    from engsrt import WhisperTranscriber
    from en_to_ko import OpenAITranslator # DeepL이 아니라 OpenAI입니다!
except ImportError as e:
    print(f"❌ [오류] 모듈을 찾을 수 없습니다: {e}")
    print("👉 audio.py, engsrt.py, en_to_ko.py 파일이 app.py와 같은 폴더에 있는지 확인하세요.")

app = Flask(__name__)
load_dotenv() # .env 파일에서 API 키 로드

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 모델 크기
MODEL_SIZE = "small"

print("⚙️ [시스템 기동] AI 자막 생성기 초기화 중...")

# 1. 오디오 추출기 (audio.py)
# (친구 코드에 따라 인자가 다를 수 있어 유연하게 처리)
try:
    extractor = AudioExtractor(BASE_DIR)
except:
    extractor = AudioExtractor() # 인자가 필요 없는 경우

# 2. Whisper 자막 생성기 (engsrt.py)
transcriber = WhisperTranscriber(model_size=MODEL_SIZE)

# 3. OpenAI 번역기 (en_to_ko.py)
api_key = os.getenv("API_KEY")
if not api_key:
    print("⚠️ [경고] .env 파일에 API_KEY가 없습니다. 번역 기능이 작동하지 않습니다.")

translator = OpenAITranslator(api_key=api_key)

print("✅ 시스템 준비 완료! 웹서버를 시작합니다.")


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
                # 1. 오디오 추출
                audio_path = extractor.extract(video_path)
                
                # 2. Whisper 영어 자막 생성
                segments = transcriber.run_whisper(audio_path)
                eng_subtitles = transcriber.create_srt_content(segments)
                
                # 영어 자막 저장
                base_name = os.path.splitext(filename)[0]
                eng_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_en.srt")
                transcriber.save_srt_file(eng_subtitles, eng_srt_path)

                final_download_path = eng_srt_path

                # 3. 한글 번역 (OpenAI)
                if translator.client:
                    print("[INFO] 한글 번역을 시작합니다...")
                    kor_subtitles = transcriber.translate_subtitles(eng_subtitles, translator)
                    
                    kor_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_ko.srt")
                    transcriber.save_srt_file(kor_subtitles, kor_srt_path)
                    final_download_path = kor_srt_path
                else:
                    print("[WARN] 번역기가 준비되지 않아 영어 자막만 다운로드합니다.")
                
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
    # 5001번 포트로 실행
    app.run(debug=True, port=5001)