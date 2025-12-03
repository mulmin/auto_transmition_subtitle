import os
import tempfile
import logging
from moviepy.editor import VideoFileClip

class AudioExtractor:
    def __init__(self, project_dir):
        pass  # tempfile 사용으로 project_dir은 불필요하지만 호출 호환성 유지

    def extract(self, video_path):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"파일 없음: {video_path}")

        # 임시 파일 생성 (main.py에서 사용 후 삭제하도록 delete=False)
        temp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = temp.name
        temp.close()

        try:
            # Context Manager로 리소스 자동 해제
            with VideoFileClip(video_path) as clip:
                if not clip.audio:
                    raise ValueError("오디오 트랙이 없습니다.")
                
                # 불필요한 로그 끄고 추출
                clip.audio.write_audiofile(output_path, codec='mp3', verbose=False, logger=None)
            
            return output_path

        except Exception as e:
            # 실패 시 임시 파일 즉시 정리
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e