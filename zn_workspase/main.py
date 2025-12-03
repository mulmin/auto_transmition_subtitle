import os
import sys
import logging
import shutil
import traceback
from dotenv import load_dotenv  # [추가] 환경변수 로드용

# 현재 파일(main.py)이 있는 폴더 경로를 가져옵니다.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 로컬 모듈 임포트
try:
    from audio import AudioExtractor
    from engsrt import WhisperTranscriber
    from en_to_ko import OpenAITranslator
except ImportError as e:
    print(f"[FATAL] 필수 모듈 로드 실패: {e}")
    sys.exit(1)


VIDEO_FILE_PATH = r"Carly Rae Jepsen - Call Me Maybe.mp4" 
MODEL_SIZE = "small"


# 1. 로깅
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# 2. FFmpeg
def check_ffmpeg():
    # 1순위: 시스템 PATH 확인 (shutil.which)
    if shutil.which("ffmpeg"):
        logging.info("✅ 시스템 PATH에서 ffmpeg 감지됨.")
        return True
    
    # 2순위: 프로젝트 폴더 내 확인
    local_ffmpeg = os.path.join(PROJECT_DIR, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        logging.info(f"✅ 프로젝트 폴더 내 ffmpeg 감지됨: {local_ffmpeg}")
        # subprocess 호출을 위해 환경변수에 추가
        os.environ["PATH"] += os.pathsep + PROJECT_DIR
        return True
        
    logging.error("❌ ffmpeg를 찾을 수 없습니다. 설치 또는 실행 파일 확인이 필요합니다.")
    return False

def main():
    setup_logging()
    
    # [추가] .env 파일 로드
    load_dotenv()
    
    logging.info(f"작업 시작: {PROJECT_DIR}")
    logging.info(f"대상 파일: {VIDEO_FILE_PATH}")
    
    # 영상 파일 존재 확인
    target_video = os.path.abspath(os.path.join(PROJECT_DIR, VIDEO_FILE_PATH))
    if not os.path.exists(target_video):
        logging.error(f"파일이 존재하지 않습니다: {target_video}")
        sys.exit(1)

    # FFmpeg 체크
    if not check_ffmpeg():
        sys.exit(1)

    # 객체 초기화
    try:
        audio_extractor = AudioExtractor(PROJECT_DIR)
        stt_worker = WhisperTranscriber(model_size=MODEL_SIZE)
        
        # [수정] API 키를 가져와서 번역기에 전달
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logging.warning("⚠️ .env 파일에서 OPENAI_API_KEY를 찾을 수 없습니다. 번역 기능이 작동하지 않을 수 있습니다.")
        
        translator = OpenAITranslator(api_key=openai_api_key)
        
    except Exception as e:
        logging.error(f"객체 초기화 중 오류 발생: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)

    audio_path = None
    exit_code = 0 # 정상 종료 코드

    try:
        # [Step 1] 오디오 추출
        logging.info(">>> [1/4] 오디오 추출 시작")
        audio_path = audio_extractor.extract(target_video)
        logging.info(f"오디오 추출 완료: {audio_path}")
        
        # [Step 2] Whisper 자막 생성
        logging.info(">>> [2/4] Whisper 자막 생성 중...")
        segments = stt_worker.run_whisper(audio_path)
        eng_subtitles = stt_worker.create_srt_content(segments)
        
        # [Step 3] 영문 SRT 저장
        output_dir = os.path.dirname(target_video)
        base_name = os.path.splitext(os.path.basename(target_video))[0]
        
        eng_srt_path = os.path.join(output_dir, f"{base_name}_en.srt")
        logging.info(f">>> [3/4] 영문 자막 저장: {eng_srt_path}")
        stt_worker.save_srt_file(eng_subtitles, eng_srt_path)

        # [Step 4] 번역
        # client가 정상적으로 생성되었는지 확인
        if translator.client:
            logging.info(">>> [4/4] 한글 번역 시작")
            kor_subtitles = stt_worker.translate_subtitles(eng_subtitles, translator)
            kor_srt_path = os.path.join(output_dir, f"{base_name}_ko.srt")
            stt_worker.save_srt_file(kor_subtitles, kor_srt_path)
            logging.info(f"완료: 한글 자막 저장됨 ({kor_srt_path})")
        else:
            logging.warning("번역기가 초기화되지 않아 번역 단계를 건너뜁니다.")

    except Exception as e:
        logging.error(f"작업 중 치명적인 오류 발생: {e}")
        logging.error(traceback.format_exc()) 
        exit_code = 1
        
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logging.info("임시 오디오 파일 삭제됨.")
            except Exception as e:
                logging.warning(f"임시 파일 삭제 실패: {e}")
        
        logging.info(f"작업 종료 (Exit Code: {exit_code})")
        sys.exit(exit_code)

if __name__ == '__main__':
    main()