import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging

# 팀원(친구)들의 모듈 가져오기
from audio import AudioExtractor
from engsrt import WhisperTranscriber
from en_to_ko import OpenAITranslator # [변경] DeepL -> OpenAITranslator

# 로깅 설정 (친구 코드가 logging을 써서 추가함)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
load_dotenv() # .env 파일 로드

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 모델 크기
MODEL_SIZE = "small"

print("⚙️ [초기화] 시스템 준비 중...")

# 1. 오디오 추출기 준비
extractor = AudioExtractor(BASE_DIR)

# 2. Whisper 자막기 준비
transcriber = WhisperTranscriber(model_size=MODEL_SIZE)

# 3. OpenAI 번역기 준비 [핵심 변경 사항!]
# .env 파일에서 API 키를 꺼내서 친구 코드(OpenAITranslator)에 넘겨줍니다.
api_key = os.getenv("API_KEY")
translator = OpenAITranslator(api_key=api_key)

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

                # 3. OpenAI 한글 번역 (친구의 engsrt.py 사용)
                if translator.client: # 번역기가 정상 연결됐다면
                    print("[INFO] OpenAI 번역 시작...")
                    
                    # 친구의 engsrt.py에 있는 함수를 그대로 호출!
                    # (친구 코드가 알아서 병렬 처리하고 OpenAI로 번역함)
                    kor_subtitles = transcriber.translate_subtitles(eng_subtitles, translator)
                    
                    kor_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_ko.srt")
                    transcriber.save_srt_file(kor_subtitles, kor_srt_path)
                    final_download_path = kor_srt_path
                else:
                    print("[WARN] API 키 문제로 번역을 건너뜁니다.")
                
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
    app.run(debug=True, port=5001)