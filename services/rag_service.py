import time
from datetime import timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import datetime
from urllib import response

from google.genai import types
from .gemini_client import get_client
from api.schemas import BiddingNoticeResponse

client = get_client()

def get_system_instruction() -> str:
    # 현재 파일의 위치를 기준으로 prompts/system_v1.txt 경로 계산
    base_path = Path(__file__).parent.parent
    prompt_path = base_path / "prompts" / "system_v1.txt"
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # 파일이 없을 경우를 대비한 기본값 또는 에러 처리
        return "기본 시스템 지시사항입니다."

# 입찰 조달문서 도우미 전용 프롬프트
SYSTEM_INSTRUCTION = get_system_instruction()

def query_rag(
    user_query: str, 
    store_name: str, 
    model: str = "gemini-3-flash-preview",
    temperature: float = 0.0
) -> Optional[BiddingNoticeResponse]:
    """문서 기반 질의응답 실행"""
    
    # File Search Tool 설정
    tool = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[store_name]
        )
    )
    
    raw_response_schema = {
        "type": "OBJECT",
        "properties": {
            "sections": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {
                            "type": "STRING",
                            "description": "섹션의 제목"
                        },
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "STRING"
                            },
                            "description": "섹션 내 상세 항목 리스트"
                        }
                    },
                    "required": ["title", "items"]
                }
            }
        },
        "required": ["sections"]
    }
    
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[tool],
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=raw_response_schema,
    )

    # 답변 생성
    resp = client.models.generate_content(
        model=model,
        contents=user_query,
        config=cfg,
    )
    # 결과 파싱
    data = resp.parsed
    try:
        response_obj = BiddingNoticeResponse(
            sections=data.get("sections", [])
        )
        return response_obj
    except Exception as e:
        return None