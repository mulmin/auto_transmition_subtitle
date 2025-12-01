import os
import whisper
import srt
from datetime import timedelta
import sys

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = self._load_model()

    def _load_model(self):
        """Whisper 모델 로드 (내부적으로만 사용)"""
        print(f"[STATUS] Whisper '{self.model_size}' 모델 로드 시작...")
        try:
            model = whisper.load_model(self.model_size)
            print(f"[STATUS] Whisper 모델 로드 완료.")
            return model
        except Exception as e:
            print(f"[ERROR] 모델 로드 실패: {e}")
            sys.exit(1)

    def run_whisper(self, audio_path):
        """오디오를 텍스트로 변환(Transcribe)하여 세그먼트 리스트 반환"""
        print("[STATUS] 2/4. 음성 인식(STT) 시작...")
        result = self.model.transcribe(
            audio=audio_path, 
            language="en",          
            word_timestamps=True    
        )
        return result["segments"]

    def create_srt_content(self, segments):
        """Whisper 결과를 srt 라이브러리 객체 리스트로 변환"""
        subtitles = []
        for i, segment in enumerate(segments):
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
        return subtitles

    def save_srt_file(self, subtitles, output_path):
        """SRT 객체 리스트를 파일로 저장"""
        final_srt_content = srt.compose(subtitles)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_srt_content)
        print(f"[STATUS] 파일 저장 완료: {os.path.basename(output_path)}")

    def translate_subtitles(self, subtitles, translator):
        """
        영문 자막 객체 리스트를 받아 번역된 자막 객체 리스트를 반환
        :param subtitles: srt.Subtitle 객체 리스트
        :param translator: DeepLTranslator 인스턴스 (팀장님 코드)
        """
        print("[STATUS] 4/4. 자막 번역 시작 (DeepL)...")
        translated_subtitles = []
        
        for sub in subtitles:
            # 원본(영어) 텍스트 번역 실행
            translated_text = translator.translate(sub.content, target_lang="KO")
            
            # 번역된 내용으로 새로운 자막 객체 생성 (시간은 동일)
            new_sub = srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=translated_text
            )
            translated_subtitles.append(new_sub)
            
        return translated_subtitles