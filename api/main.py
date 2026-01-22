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
@app.post("/v1/documents/upload")
async def upload_document(file: UploadFile = File(...), scope: Optional[str] = Form(None)):
    """입찰 관련 문서를 업로드하고 인덱싱합니다."""
    try:
        # 임시 파일 저장
        temp_file_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 파일 인덱싱
        #file_service.index_file(STORE_NAME, temp_file_path, scope=scope)
        file_service.upload_to_store(STORE_NAME, temp_file_path, file.filename, scope=scope)

        # 임시 파일 삭제
        os.remove(temp_file_path)

        return {"status": "success", "message": f"파일 '{file.filename}'이(가) 성공적으로 업로드 및 인덱싱되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# [3] AI 질의응답(RAG) 엔드포인트
# ---------------------------------------------------------
