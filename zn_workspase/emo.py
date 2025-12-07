import logging
import torch
import librosa
from transformers import AutoModelForAudioClassification, Wav2Vec2FeatureExtractor

class EmotionRecognizer:
    def __init__(self, model_name=None):
        # [수정] 호환성 문제가 있는 모델 대신, 표준 벤치마크 모델(SUPERB)로 변경
        # 이 모델은 에러 없이 안정적으로 작동하며 성능도 우수합니다.
        self.model_name = model_name or "superb/wav2vec2-base-superb-er"
        logging.info(f"[Emotion] 모델 초기화: {self.model_name}")
        self._load_model()

    def _load_model(self):
        try:
            # AutoModel을 사용하여 모델 구조 자동 매칭
            self.model = AutoModelForAudioClassification.from_pretrained(self.model_name)
            self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_name)
            self.model.eval()
        except Exception as e:
            logging.error(f"[Emotion] 모델 로드 실패: {e}")
            raise e

    def predict_emotion(self, audio_path, start_sec, end_sec):
        try:
            duration = end_sec - start_sec
            if duration < 0.5: return "neutral"

            # librosa로 오디오 로드
            speech, _ = librosa.load(audio_path, sr=16000, offset=start_sec, duration=duration)
            
            # 입력값 전처리
            inputs = self.feature_extractor(
                speech, 
                sampling_rate=16000, 
                return_tensors="pt", 
                padding=True
            )

            # 예측 실행
            with torch.no_grad():
                logits = self.model(inputs.input_values).logits
                predicted_ids = torch.argmax(logits, dim=-1)
            
            # 결과 라벨 변환
            label = self.model.config.id2label[predicted_ids.item()]
            
            # [보정] SUPERB 모델은 'neutral'을 'neu'로 출력하므로 변환 필요
            if label == 'neu':
                label = 'neutral'
                
            return label

        except Exception as e:
            logging.debug(f"감정 분석 실패: {e}")
            return "neutral"