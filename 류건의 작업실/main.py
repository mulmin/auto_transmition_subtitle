import os
import whisper
import srt
import sys
from moviepy.editor import VideoFileClip 
from datetime import timedelta

# --- 사용자 설정 ---
# 1. 자막을 추출할 동영상 파일 경로를 여기에 입력하세요.
VIDEO_FILE_PATH = "Carly Rae Jepsen - Call Me Maybe.mp4" 

# 2. Whisper 모델 크기 (작을수록 빠르지만 정확도는 낮아짐)
MODEL_SIZE = "base"
# ------------------

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 모델 로드 시작/완료
print(f"[STATUS] Whisper '{MODEL_SIZE}' 모델 로드 시작...")
try:
    WHISPER_MODEL = whisper.load_model(MODEL_SIZE)
    print(f"[STATUS] Whisper '{MODEL_SIZE}' 모델 로드 완료.")
except:
    print("[ERROR] Whisper 모델 로드 실패. 프로그램을 종료합니다.")
    sys.exit(1)


def extract_audio(video_path):
    if not os.path.exists(video_path):
        raise FileNotFoundError
        
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(PROJECT_DIR, f"{base_name}_temp_audio.mp3")
    
    # 2. 오디오 추출 시작
    print("[STATUS] 1/3. 동영상에서 오디오 추출 시작...")
    video_clip = VideoFileClip(video_path)
    video_clip.audio.write_audiofile(
        audio_path, 
        codec='mp3', 
        logger=None
    )
    video_clip.close()
    return audio_path


def generate_srt(audio_path):
    # 3. STT(자막 생성) 시작
    print("[STATUS] 2/3. 음성 인식을 통한 영어 자막 생성 시작...")
    result = WHISPER_MODEL.transcribe(
        audio=audio_path, 
        language="en",          
        word_timestamps=True    
    )

    subtitles = []
    for i, segment in enumerate(result["segments"]):
        start_ms = int(segment['start'] * 1000)
        end_ms = int(segment['end'] * 1000)
        
        subtitles.append(
            srt.Subtitle(
                index=i + 1,
                start=timedelta(milliseconds=start_ms),
                end=timedelta(milliseconds=end_ms),
                content=segment['text'].strip()
            )
        )

    srt_filename = os.path.splitext(os.path.basename(audio_path))[0].replace('_temp_audio', '_en') + ".srt"
    srt_path = os.path.join(PROJECT_DIR, srt_filename)
    
    final_srt_content = srt.compose(subtitles)
    
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(final_srt_content)
        
    # 4. SRT 파일 저장 완료
    print(f"[STATUS] 3/3. 영어 SRT 파일 저장 완료: {os.path.basename(srt_path)}")
    return srt_path


def main():
    audio_path = None
    try:
        audio_path = extract_audio(VIDEO_FILE_PATH)
        generate_srt(audio_path)
        
    except FileNotFoundError:
        print(f"[ERROR] 파일을 찾을 수 없습니다: {VIDEO_FILE_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 처리 중 알 수 없는 오류 발생: {e}")
        sys.exit(1)
        
    finally:
        # 5. 임시 파일 정리 완료
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[STATUS] 임시 오디오 파일 정리 완료.")
        
        print("\n✨ 모든 과정 완료. 프로젝트의 다음 단계인 번역을 시작할 준비가 되었습니다.")


if __name__ == '__main__':
    main()