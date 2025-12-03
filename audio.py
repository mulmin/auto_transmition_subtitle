import os
from moviepy.editor import VideoFileClip

class AudioExtractor:
    def __init__(self, project_dir):
        self.project_dir = project_dir

    def extract(self, video_path):
        """동영상에서 오디오를 추출하여 mp3로 저장"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {video_path}")
        
        print("[STATUS] 1/4. 동영상에서 오디오 추출 시작...")
        
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(self.project_dir, f"{base_name}_temp_audio.mp3")
        
        try:
            video_clip = VideoFileClip(video_path)
            video_clip.audio.write_audiofile(
                audio_path, 
                codec='mp3', 
                logger=None # 로그 출력 최소화
            )
            video_clip.close()
            return audio_path
        except Exception as e:
            print(f"[ERROR] 오디오 추출 중 오류: {e}")
            raise e