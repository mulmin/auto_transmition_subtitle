import os
import tempfile
import logging
from moviepy.editor import VideoFileClip

class AudioExtractor:
    def extract(self, video_path):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"파일 없음: {video_path}")

        logging.info(">>> [1/4] 오디오 추출 중...")
        
        # 임시 파일 생성 (삭제 방지 옵션 필수)
        temp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = temp.name
        temp.close()

        try:
            with VideoFileClip(video_path) as clip:
                if not clip.audio:
                    raise ValueError("오디오 트랙 없음")
                
                clip.audio.write_audiofile(
                    output_path, 
                    codec='mp3', 
                    verbose=False, 
                    logger=None
                )
            return output_path

        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e