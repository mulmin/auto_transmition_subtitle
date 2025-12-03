import os
import sys

# 현재 파일(main.py)이 있는 폴더 경로를 가져옵니다.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


from audio import AudioExtractor
from engsrt import WhisperTranscriber
from en_to_ko import DeepLTranslator
# 팀장님 번역 모듈 임포트 시도


# --- 사용자 설정 ---
VIDEO_FILE_PATH = "류건의 작업실\Carly Rae Jepsen - Call Me Maybe.mp4" 
MODEL_SIZE = "small"
# ------------------

def main():
    print(f"[설정 확인] 현재 작업 경로: {PROJECT_DIR}")
    
    # ffmpeg.exe 존재 여부 체크
    ffmpeg_path = os.path.join(PROJECT_DIR, "ffmpeg.exe")
    if os.path.exists(ffmpeg_path):
        print(f"[설정 확인] ✅ ffmpeg.exe가 정상적으로 감지되었습니다.")
    else:
        print(f"[설정 확인] ⚠️ 경고: 폴더 내에 ffmpeg.exe가 보이지 않습니다.")
        print("          시스템 PATH에 설치되어 있지 않다면 오류가 날 수 있습니다.")

    # 0. 객체 초기화
    audio_extractor = AudioExtractor(PROJECT_DIR)
    stt_worker = WhisperTranscriber(model_size=MODEL_SIZE)
    translator = DeepLTranslator()

    audio_path = None
    
    try:
        # 1. 오디오 추출
        audio_path = audio_extractor.extract(VIDEO_FILE_PATH)
        
        # 2. Whisper로 영문 자막 데이터 생성
        segments = stt_worker.run_whisper(audio_path)
        eng_subtitles = stt_worker.create_srt_content(segments)
        
        # 3. 영문 SRT 파일 저장
        base_name = os.path.splitext(os.path.basename(VIDEO_FILE_PATH))[0]
        eng_srt_path = os.path.join(PROJECT_DIR, f"{base_name}_en.srt")
        print(f"[STATUS] 3/4. 영어 자막 저장 중...")
        stt_worker.save_srt_file(eng_subtitles, eng_srt_path)

        # 4. 자막 번역 및 한글 SRT 저장
        if translator.translator:
            kor_subtitles = stt_worker.translate_subtitles(eng_subtitles, translator)
            kor_srt_path = os.path.join(PROJECT_DIR, f"{base_name}_ko.srt")
            stt_worker.save_srt_file(kor_subtitles, kor_srt_path)
        else:
            print("[WARN] 번역기 초기화 실패로 번역 단계는 건너뜁니다.")

    except Exception as e:
        print(f"\n[ERROR] 작업 중 치명적인 오류 발생: {e}")
        import traceback
        traceback.print_exc() # 자세한 에러 위치 출력
        sys.exit(1)
        
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"[STATUS] 임시 오디오 파일 정리 완료.")
            except:
                pass
        
        print("\n✨ 모든 과정이 완료되었습니다!")

if __name__ == '__main__':
    main()