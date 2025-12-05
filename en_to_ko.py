# 파이썬 인터프리터 경로 확인
# import sys
# print(sys.executable)

import deepl
from dotenv import load_dotenv
import os

class DeepLTranslator:
    def __init__(self):
        
        try:
            # 1. 번역기 초기화
            load_dotenv()

            self.api_key = os.getenv("API_KEY")
            self.translator = deepl.Translator(self.api_key)
            
            
            # 2. 키가 유효한지 살짝 테스트 (사용량 확인으로 검증)
            usage = self.translator.get_usage()
            print(f"✅ DeepL 번역기 연결 성공! (남은 용량: {usage.character.limit - usage.character.count}자)")
            
        except deepl.AuthorizationException:
            print("❌ [오류] API 키가 잘못되었습니다. 다시 확인해주세요.")
            self.translator = None
        except Exception as e:
            print(f"❌ [오류] 초기화 중 문제 발생: {e}")
            self.translator = None

    def translate(self, text, target_lang="KO"):
        """
        텍스트를 번역하는 메서드
        :param text: 번역할 영어 텍스트
        :param target_lang: 목표 언어 코드 (기본값: KO - 한국어)
        :return: 번역된 텍스트 (실패 시 에러 메시지 반환)

        중요 사항: text만 입력하면 가능함
        """
        # 초기화 실패했거나 텍스트가 비어있으면 중단
        if not self.translator:
            return "[시스템] 번역기가 초기화되지 않았습니다."
        if not text or text.strip() == "":
            return ""

        try:
            # 번역 실행
            result = self.translator.translate_text(text, target_lang=target_lang)
            return result.text
            
        except deepl.QuotaExceededException:
            return "❌ [오류] 이번 달 무료 번역 용량을 모두 사용했습니다."
        except deepl.ConnectionException:
            return "❌ [오류] 인터넷 연결을 확인해주세요."
        except Exception as e:
            return f"❌ [오류] 번역 중 알 수 없는 에러: {e}"

    def get_usage_status(self):
        """현재 사용량 정보를 텍스트로 반환"""
        if not self.translator: return "확인 불가"
        
        try:
            usage = self.translator.get_usage()
            if usage.character.limit:
                percent = (usage.character.count / usage.character.limit) * 100
                return f"사용량: {usage.character.count}/{usage.character.limit} 자 ({percent:.1f}%)"
            return "무제한 요금제 사용 중"
        except:
            return "사용량 정보 조회 실패"