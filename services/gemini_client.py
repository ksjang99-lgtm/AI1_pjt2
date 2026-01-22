import os
from dotenv import load_dotenv
from google import genai

# 환경 변수 로드
load_dotenv()

API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
STORE_NAME = (os.getenv("FILE_SEARCH_STORE_NAME") or "").strip()

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

# 전역 Client 인스턴스 생성
client = genai.Client(api_key=API_KEY)

def get_client():
    """API 호출 시 사용할 Client 인스턴스 반환"""
    return client

def get_default_store_name():
    """.env에 정의된 기본 Store Name 반환"""
    return STORE_NAME