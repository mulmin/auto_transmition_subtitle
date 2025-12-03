from openai import OpenAI
from dotenv import load_dotenv
import os

class OpenAITranslator:
    def __init__(self, api_key, model="gpt-4o-mini"):

        self.api_key = api_key
        self.model = model
    
        try:
            self.client = OpenAI(api_key=api_key)
            print(f"✅ OpenAI 번역기 초기화 성공! (모델: {self.model})")
        except Exception as e:
            print(f"❌ [오류] OpenAI 클라이언트 초기화 실패: {e}")
            self.client = None

    def translate(self, text, emotion=None):
        """
        텍스트를 번역하는 메서드
        :param text: 번역할 영어 텍스트
        :param emotion: (선택) 감정 상태 (예: 'angry', 'sad'). None이면 일반 번역.
        """
        if not self.client:
            return "[시스템] 번역기가 초기화되지 않았습니다."
        if not text or text.strip() == "":
            return ""

        try:
            # 1. 기본 프롬프트 설정 (시스템 역할 부여)
            system_prompt = "You are a professional subtitle translator. Translate the English text into natural Korean."
            user_prompt = f"Text: '{text}'"

            # =================================================================
            # 🔒 [감정 모듈] (현재 비활성화됨: 나중에 주석을 풀어서 사용하세요)
            # =================================================================
            # if emotion and emotion != "neutral":
            #     # 시스템 프롬프트에 감정 반영 지시 추가
            #     system_prompt += " The speaker is feeling a specific emotion. Reflect this emotion in the Korean translation style (honorifics, ending, nuance)."
            #     # 사용자 입력에 감정 정보 추가
            #     user_prompt += f"\nSpeaker's Emotion: {emotion}"
            # =================================================================

            # 2. OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3  # 0에 가까울수록 직역, 높을수록 창의적(의역)
            )

            # 3. 결과 반환
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"❌ [오류] OpenAI 번역 중 에러 발생: {e}"