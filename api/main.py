from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List, Optional
import os
import shutil

# 앞서 작성한 서비스 레이어 임포트
from services import file_service, rag_service, gemini_client

app = FastAPI(title="스타빌 입찰 지원 RAG API")

# .env에서 설정한 기본 스토어 이름 사용
STORE_NAME = gemini_client.get_default_store_name()

# ---------------------------------------------------------
# [1] 문서 목록 조회 엔드포인트
# ---------------------------------------------------------
@app.get("/v1/documents/list")
async def get_documents(scope: Optional[str] = None):
    """현재 인덱싱된 입찰 관련 문서 목록을 반환합니다."""
    try:
        files = file_service.list_files(STORE_NAME, scope=scope)
        return {"status": "success", "data": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# [2] 문서 업로드 및 인덱싱 엔드포인트
# ---------------------------------------------------------

# ---------------------------------------------------------
# [3] AI 질의응답(RAG) 엔드포인트
# ---------------------------------------------------------
