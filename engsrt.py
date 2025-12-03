import os
import sys
import logging
import whisper
import srt
from datetime import timedelta
import concurrent.futures

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
                word_timestamps=True,   # [중요] 단어별 시간 정보를 얻기 위해 필수
                verbose=False
            )
            return result["segments"]
        except Exception as e:
            logging.error(f"Whisper 실행 중 오류: {e}")
            raise e

    def create_srt_content(self, segments):
        """
        [핵심 수정] 
        Whisper의 긴 세그먼트를 단어(word) 단위로 쪼개서 
        짧은 호흡의 자막으로 재구성합니다.
        """
        subtitles = []
        subtitle_index = 1
        
        # [설정] 한 자막당 최대 글자 수 (이걸 줄이면 자막이 더 자주 바뀝니다)
        MAX_CHARS_PER_LINE = 40 

        for segment in segments:
            # 단어 정보가 없으면(구버전 모델 등) 그냥 통째로 처리
            if 'words' not in segment:
                start_ms = int(segment['start'] * 1000)
                end_ms = int(segment['end'] * 1000)
                subtitles.append(srt.Subtitle(subtitle_index, timedelta(milliseconds=start_ms), timedelta(milliseconds=end_ms), segment['text'].strip()))
                subtitle_index += 1
                continue

            # 단어들을 모아서 새로운 문장 만들기
            current_words = []
            current_len = 0

            for word_info in segment['words']:
                word = word_info['word'].strip()
                current_words.append(word_info)
                current_len += len(word) + 1 # 공백 포함 길이 계산

                # 글자 수가 꽉 찼거나, 문장이 끝나는 기호가 있으면 자막 자르기
                if current_len >= MAX_CHARS_PER_LINE or word.endswith(('.', '?', '!')):
                    if not current_words: continue

                    # 모인 단어들의 시작과 끝 시간 계산
                    start_time = timedelta(seconds=current_words[0]['start'])
                    end_time = timedelta(seconds=current_words[-1]['end'])
                    text = " ".join([w['word'].strip() for w in current_words])

                    subtitles.append(srt.Subtitle(
                        index=subtitle_index,
                        start=start_time,
                        end=end_time,
                        content=text
                    ))
                    subtitle_index += 1
                    
                    # 초기화
                    current_words = []
                    current_len = 0
            
            # 남은 찌꺼기 단어들 처리
            if current_words:
                start_time = timedelta(seconds=current_words[0]['start'])
                end_time = timedelta(seconds=current_words[-1]['end'])
                text = " ".join([w['word'].strip() for w in current_words])

                subtitles.append(srt.Subtitle(
                    index=subtitle_index,
                    start=start_time,
                    end=end_time,
                    content=text
                ))
                subtitle_index += 1

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
        """영문 자막 -> 한글 자막 번역 (병렬 처리)"""
        logging.info(">>> [4/4] 자막 번역 시작 (OpenAI 병렬 처리)...")
        
        translated_subtitles = [None] * len(subtitles)

        def process_single_subtitle(index, sub):
            clean_text = sub.content.replace("\n", " ")
            try:
                translated_text = translator.translate(clean_text)
            except Exception as e:
                logging.warning(f"번역 실패: {e}")
                translated_text = sub.content
            
            return index, srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=translated_text
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_sub = {
                executor.submit(process_single_subtitle, i, sub): sub 
                for i, sub in enumerate(subtitles)
            }
            
            for future in concurrent.futures.as_completed(future_to_sub):
                try:
                    index, new_sub = future.result()
                    translated_subtitles[index] = new_sub
                except Exception as exc:
                    logging.error(f"쓰레드 오류: {exc}")

        for i, sub in enumerate(translated_subtitles):
            if sub is None:
                translated_subtitles[i] = subtitles[i]

        return translated_subtitles