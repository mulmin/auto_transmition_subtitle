import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

# 팀원들이 만든 모듈 가져오기 (Import)
from audio import AudioExtractor
from engsrt import WhisperTranscriber
from en_to_ko import DeepLTranslator

app = Flask(__name__)

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 모델 크기 설정 (팀원 코드 기본값인 small 사용)
MODEL_SIZE = "small"

# --- 객체 초기화 (서버 켤 때 한 번만 준비) ---
print("⚙️ 시스템 초기화 중...")
extractor = AudioExtractor(UPLOAD_FOLDER) # 오디오 추출기
transcriber = WhisperTranscriber(model_size=MODEL_SIZE) # Whisper 자막기
translator = DeepLTranslator() # DeepL 번역기
print("✅ 시스템 준비 완료!")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. 파일 받기
        if 'video_file' not in request.files: return '파일 없음'
        file = request.files['video_file']
        if file.filename == '': return '선택 안함'

        if file:
            filename = secure_filename(file.filename)
            video_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(video_path)

            audio_path = None
            try:
                # ----------------------------------------------
                # 팀원들의 코드 로직 실행
                # ----------------------------------------------
                
                # 2. 오디오 추출 (audio.py 사용)
                # (팀원 코드는 저장 경로를 내부에서 정하므로 video_path만 넘김)
                audio_path = extractor.extract(video_path)
                
                # 3. Whisper로 영어 자막 생성 (engsrt.py 사용)
                segments = transcriber.run_whisper(audio_path)
                eng_subtitles = transcriber.create_srt_content(segments)
                
                # 영어 자막 파일명 설정
                base_name = os.path.splitext(filename)[0]
                eng_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_en.srt")
                transcriber.save_srt_file(eng_subtitles, eng_srt_path)

                # 4. DeepL로 한글 번역 (en_to_ko.py 사용)
                final_download_path = eng_srt_path # 기본은 영어 자막 다운로드

                if translator.translator: # 번역기가 정상 연결되었다면
                    print("[INFO] 한글 번역을 시작합니다...")
                    kor_subtitles = transcriber.translate_subtitles(eng_subtitles, translator)
                    
                    # 한글 자막 파일 저장
                    kor_srt_path = os.path.join(UPLOAD_FOLDER, f"{base_name}_ko.srt")
                    transcriber.save_srt_file(kor_subtitles, kor_srt_path)
                    
                    # 다운로드 대상을 한글 자막으로 변경
                    final_download_path = kor_srt_path
                else:
                    print("[WARN] DeepL 키가 없거나 오류가 있어 영어 자막만 제공합니다.")

                # 5. 결과 파일 다운로드 (한글 자막 우선, 없으면 영어)
                return send_file(final_download_path, as_attachment=True)

            except Exception as e:
                return f"❌ 에러 발생: {str(e)}"
            finally:
                # 청소: 원본 영상과 추출된 오디오 삭제
                if os.path.exists(video_path): os.remove(video_path)
                if audio_path and os.path.exists(audio_path): os.remove(audio_path)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
