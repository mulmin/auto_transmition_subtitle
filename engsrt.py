import os
import sys
import logging
import whisper
import srt
from datetime import timedelta
import concurrent.futures  # 병렬 처리를 위한 모듈 (속도 향상)

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = self._load_model()

    def _load_model(self):
        """Whisper 모델 로드"""
        logging.info(f"Whisper '{self.model_size}' 모델 로드 시작...")
        try:
            model = whisper.load_model(self.model_size)
            logging.info("Whisper 모델 로드 완료.")
            return model
        except Exception as e:
            logging.error(f"모델 로드 실패: {e}")
            sys.exit(1)

    def run_whisper(self, audio_path):
        """오디오를 텍스트로 변환 (Transcribe)"""
        logging.info(">>> [2/4] 음성 인식(STT) 분석 중...")
        try:
            result = self.model.transcribe(
                audio=audio_path, 
                language="en",          
                word_timestamps=True,   # 정교한 타임스탬프 사용
                verbose=False           # 불필요한 콘솔 출력 끄기
            )
            return result["segments"]
        except Exception as e:
            logging.error(f"Whisper 실행 중 오류: {e}")
            raise e

    def create_srt_content(self, segments):
        """Whisper 결과를 srt 객체 리스트로 변환"""
        subtitles = []
        # 요청하신 대로 글자수 제한(max_char) 및 줄바꿈 로직을 제거했습니다.

        for i, segment in enumerate(segments):
            start_ms = int(segment['start'] * 1000)
            end_ms = int(segment['end'] * 1000)
            text = segment['text'].strip()

            # 줄바꿈 처리 없이 있는 그대로 자막 생성
            subtitles.append(
                srt.Subtitle(
                    index=i + 1,
                    start=timedelta(milliseconds=start_ms),
                    end=timedelta(milliseconds=end_ms),
                    content=text
                )
            )
        return subtitles

    def save_srt_file(self, subtitles, output_path):
        """SRT 파일 저장"""
        final_srt_content = srt.compose(subtitles)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_srt_content)
            logging.info(f"자막 파일 저장됨: {os.path.basename(output_path)}")
        except Exception as e:
            logging.error(f"파일 저장 실패: {e}")
            raise e

    def translate_subtitles(self, subtitles, translator):
        """영문 자막 -> 한글 자막 번역 (병렬 처리 적용으로 속도 향상)"""
        logging.info(">>> [4/4] 자막 번역 시작 (OpenAI 병렬 처리)...")
        
        # 결과를 순서대로 저장하기 위해 리스트 미리 할당
        translated_subtitles = [None] * len(subtitles)

        # 하나의 자막을 번역하는 내부 함수
        def process_single_subtitle(index, sub):
            # 혹시 모를 줄바꿈 문자만 공백으로 치환 (번역 정확도 위해)
            clean_text = sub.content.replace("\n", " ")
            try:
                translated_text = translator.translate(clean_text)
            except Exception as e:
                logging.warning(f"번역 실패 (구간 {sub.index}): {e}")
                translated_text = sub.content # 실패 시 원문 유지
            
            return index, srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=translated_text
            )

        # ThreadPoolExecutor를 사용하여 병렬 처리 (최대 5개 동시 요청)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # 모든 자막에 대해 번역 작업 예약
            future_to_sub = {
                executor.submit(process_single_subtitle, i, sub): sub 
                for i, sub in enumerate(subtitles)
            }
            
            # 작업이 완료되는 대로 결과 수집
            for future in concurrent.futures.as_completed(future_to_sub):
                try:
                    index, new_sub = future.result()
                    translated_subtitles[index] = new_sub
                except Exception as exc:
                    logging.error(f"번역 쓰레드 오류: {exc}")

        # 혹시라도 None으로 남아있는 부분이 있다면 원본으로 채움 (안전장치)
        for i, sub in enumerate(translated_subtitles):
            if sub is None:
                translated_subtitles[i] = subtitles[i]

        return translated_subtitles