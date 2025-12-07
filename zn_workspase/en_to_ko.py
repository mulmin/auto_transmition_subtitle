from openai import OpenAI

class OpenAITranslator:
    def __init__(self, api_key):
        self.client = None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"OpenAI 초기화 실패: {e}")

    def translate(self, text, emotion="neutral"):
        # 1. 예외 처리: 클라이언트가 없거나 텍스트가 비었으면 원문 반환
        if not self.client or not text: return text

        # 2. 시스템 프롬프트 설정 (역할 부여)
        # "Output ONLY the translated text" -> 번역문 외에 딴소리 하지 말라는 핵심 지시
        sys_prompt = (
            "You are a professional subtitle translator. Translate English to Korean. "
            "Output ONLY the translated text. Do NOT add notes, explanations, or parentheses."
        )
        user_prompt = f"Text: '{text}'"

        # 3. 감정 반영 지시 (괄호 사용 금지 명시)
        if emotion and emotion != "neutral":
            sys_prompt += (
                f" The speaker feels '{emotion}'. "
                "Reflect this emotion ONLY through Korean nuances, sentence endings, and punctuation. "
                "Do NOT add descriptive text like (sad) or (angry)."
            )

        try:
            # 4. API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3 # 창의성을 약간 낮춰서 이상한 멘트 방지
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return text # 에러 시 원문 반환