from typing import Dict, Any
from google.genai import types
from .gemini_client import get_client

client = get_client()

# 입찰 조달문서 도우미 전용 프롬프트
SYSTEM_INSTRUCTION = """
당신은 '스타빌 조달문서 도우미'이다.
절대 규칙:
1) 반드시 제공된 File Search store에서 검색된 근거(문서 내용)로만 답하라.
2) File Search 결과/근거가 없으면 "문서에서 확인할 수 없습니다."라고 답하라.
3) 추측/상상/일반지식으로 보완하지 말라.
4) 사용자의 질문이 문서 범위를 벗어나면, 문서에 추가로 어떤 정보가 필요할지 짧게 안내하라.
"""

def query_rag(
    user_query: str, 
    store_name: str, 
    model: str = "gemini-3-flash-preview",
    temperature: float = 0.0
) -> Dict[str, Any]:
    """문서 기반 질의응답 실행"""
    
    # File Search Tool 설정
    tool = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[store_name]
        )
    )

    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[tool],
        temperature=temperature,
    )

    # 답변 생성
    resp = client.models.generate_content(
        model=model,
        contents=user_query,
        config=cfg,
    )

    return {
        "answer": getattr(resp, "text", "문서에서 확인할 수 없습니다."),
        "raw_meta": {
            "model": model,
            "candidates": len(resp.candidates) if resp.candidates else 0
        }
    }