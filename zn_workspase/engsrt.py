import os
import sys
import logging
import whisper
import srt
import concurrent.futures
from datetime import timedelta
from emo import EmotionRecognizer

class WhisperTranscriber:
    def __init__(self, model_size="base"):
        self.model = self._load_model(model_size)
        try:
            self.emotion_recognizer = EmotionRecognizer()
        except:
            self.emotion_recognizer = None

    def _load_model(self, model_size):
        logging.info(f"Whisper '{model_size}' 로드 중...")
        return whisper.load_model(model_size)

    def run_whisper(self, audio_path):
        logging.info(">>> [2/4] Whisper 분석 중...")
        return self.model.transcribe(
            audio=audio_path, 
            language="en", 
            word_timestamps=True, 
            verbose=False
        )["segments"]

    def create_srt_content(self, segments):
        """단어(Word) 단위로 자막을 재조립하여 호흡을 짧게 만듦"""
        subtitles = []
        idx = 1
        MAX_CHARS = 40

        for seg in segments:
            if 'words' not in seg: # 단어 정보 없으면 통으로 처리
                start = timedelta(seconds=seg['start'])
                end = timedelta(seconds=seg['end'])
                subtitles.append(srt.Subtitle(idx, start, end, seg['text'].strip()))
                idx += 1
                continue

            words_buf = []
            char_count = 0

            for w in seg['words']:
                word_txt = w['word'].strip()
                words_buf.append(w)
                char_count += len(word_txt) + 1

                # 40자가 넘거나 문장 부호로 끝나면 끊기
                if char_count >= MAX_CHARS or word_txt.endswith(('.', '?', '!')):
                    if not words_buf: continue
                    
                    self._add_subtitle(subtitles, idx, words_buf)
                    idx += 1
                    words_buf = []
                    char_count = 0
            
            # 남은 단어 처리
            if words_buf:
                self._add_subtitle(subtitles, idx, words_buf)
                idx += 1

        return subtitles

    def _add_subtitle(self, subtitles, idx, word_list):
        start = timedelta(seconds=word_list[0]['start'])
        end = timedelta(seconds=word_list[-1]['end'])
        text = " ".join([w['word'].strip() for w in word_list])
        subtitles.append(srt.Subtitle(idx, start, end, text))

    def save_srt_file(self, subtitles, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(subtitles))
        logging.info(f"저장 완료: {os.path.basename(path)}")

    def translate_subtitles(self, subtitles, translator, audio_path):
        """감정 분석 + 병렬 번역"""
        logging.info(">>> [4/4] 감정 분석 및 번역 (병렬 처리)...")
        results = [None] * len(subtitles)

        def task(i, sub):
            emotion = "neutral"
            if self.emotion_recognizer:
                emotion = self.emotion_recognizer.predict_emotion(
                    audio_path, sub.start.total_seconds(), sub.end.total_seconds()
                )
            
            if emotion != "neutral":
                logging.info(f"[{i+1}] 감정: {emotion}")

            text = translator.translate(sub.content.replace("\n", " "), emotion)
            return i, srt.Subtitle(sub.index, sub.start, sub.end, text)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(task, i, sub) for i, sub in enumerate(subtitles)]
            for f in concurrent.futures.as_completed(futures):
                try:
                    i, new_sub = f.result()
                    results[i] = new_sub
                except Exception as e:
                    logging.error(f"번역 오류: {e}")

        # 실패한 부분 원본 유지
        return [res if res else subtitles[i] for i, res in enumerate(results)]