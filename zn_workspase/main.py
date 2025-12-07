import os
import sys
import logging
import shutil
import argparse
import traceback
from dotenv import load_dotenv

# 로컬 모듈
try:
    from audio import AudioExtractor
    from engsrt import WhisperTranscriber
    from en_to_ko import OpenAITranslator
except ImportError as e:
    print(f"[FATAL] 모듈 로드 실패: {e}")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def check_ffmpeg():
    if shutil.which("ffmpeg"):
        return True
    
    local_ffmpeg = os.path.join(PROJECT_DIR, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        os.environ["PATH"] += os.pathsep + PROJECT_DIR
        return True
        
    logging.error("❌ ffmpeg를 찾을 수 없습니다.")
    return False

def parse_args():
    parser = argparse.ArgumentParser(description="AI 자막 생성기")
    # 기본값 설정으로 인자 없이 실행 가능
    parser.add_argument("--video", "-v", default=r"Carly Rae Jepsen - Call Me Maybe.mp4", help="영상 경로")
    parser.add_argument("--model", "-m", default="small", help="Whisper 모델 크기")
    return parser.parse_args()

def main():
    setup_logging()
    load_dotenv()
    args = parse_args()

    # 경로 절대경로화
    video_path = os.path.abspath(args.video if os.path.isabs(args.video) else os.path.join(PROJECT_DIR, args.video))
    
    logging.info(f"=== 작업 시작: {os.path.basename(video_path)} ===")

    if not os.path.exists(video_path):
        logging.error(f"파일 없음: {video_path}")
        sys.exit(1)
    if not check_ffmpeg():
        sys.exit(1)

    try:
        # 객체 초기화
        audio_extractor = AudioExtractor()
        stt_worker = WhisperTranscriber(model_size=args.model)
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.warning("⚠️ OPENAI_API_KEY가 없습니다. 번역이 불가능할 수 있습니다.")
        translator = OpenAITranslator(api_key=api_key)

        # [Step 1] 오디오 추출
        audio_path = audio_extractor.extract(video_path)

        # [Step 2] Whisper 자막 생성
        segments = stt_worker.run_whisper(audio_path)
        eng_subtitles = stt_worker.create_srt_content(segments)
        
        # [Step 3] 영문 SRT 저장
        base_name = os.path.splitext(video_path)[0]
        stt_worker.save_srt_file(eng_subtitles, f"{base_name}_en.srt")

        # [Step 4] 번역 및 저장
        if translator.client:
            kor_subtitles = stt_worker.translate_subtitles(eng_subtitles, translator, audio_path)
            stt_worker.save_srt_file(kor_subtitles, f"{base_name}_ko.srt")
        
    except Exception as e:
        logging.error(f"작업 실패: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)
        
    finally:
        # 임시 파일 정리
        if 'audio_path' in locals() and audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logging.info("🧹 임시 오디오 삭제 완료")
            except: 
                pass

if __name__ == '__main__':
    main()