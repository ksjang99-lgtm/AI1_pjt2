import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Query
from typing import List, Optional
import os
import shutil
# from enum import Enum
# 앞서 작성한 서비스 레이어 임포트
from services import file_service, rag_service, gemini_client
from api.Enums import DocumentScope

app = FastAPI(title="스타빌 입찰 지원 RAG API")

# .env에서 설정한 기본 스토어 이름 사용
STORE_NAME = gemini_client.get_default_store_name()

# ---------------------------------------------------------
# [1] 문서 목록 조회 엔드포인트
# ---------------------------------------------------------
@app.get("/v1/documents/list")
async def get_documents(scopeEnum: Optional[DocumentScope] = Query(None)):
    """현재 인덱싱된 입찰 관련 문서 목록을 반환합니다."""
    try:
        scope = None if scopeEnum is None else scopeEnum.name
        files = file_service.list_files(STORE_NAME, scope=scope)
        return {"status": "success", "data": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# [2] 문서 업로드 및 인덱싱 엔드포인트
# ---------------------------------------------------------
@app.post("/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...), 
    scope: Optional[str] = Form("law")
):
    """입찰 관련 문서를 업로드하고 인덱싱합니다. 중복 파일은 거부합니다."""
    try:
        # 1. 중복 파일 체크 (업로드 전 미리 확인)
        # 같은 scope 내에 동일한 파일명이 있는지 확인합니다.
        existing_files = file_service.list_files(STORE_NAME, scope=scope)
        if any(f["display_name"] == file.filename for f in existing_files):
            # 409 Conflict: 서버의 현재 상태와 요청이 충돌할 때 사용
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"이미 동일한 파일명('{file.filename}')이 해당 scope('{scope}') 내에 존재합니다."
            )

        # 2. 임시 파일 저장
        # 한글 파일명 문제를 피하기 위해 로컬 저장용 임시 이름을 생성합니다.
        file_extension = os.path.splitext(file.filename)[1]
        safe_temp_filename = f"{uuid.uuid4()}{file_extension}"
        
        os.makedirs("temp", exist_ok=True)
        temp_file_path = os.path.join("temp", safe_temp_filename)

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # 3. Gemini Store 파일 업로드 및 인덱싱
            file_service.upload_to_store(STORE_NAME, temp_file_path, file.filename, scope=scope)

        finally:
            # 성공/실패 여부와 상관없이 임시 파일은 반드시 삭제
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        return {
            "status": "success", 
            "message": f"파일 '{file.filename}'이(가) 성공적으로 업로드되었습니다."
        }

    except HTTPException as he:
        # 중복 체크 등에서 발생한 HTTP 예외는 그대로 전달
        raise he
    except Exception as e:
        # 그 외 시스템 에러
        raise HTTPException(status_code=500, detail=f"업로드 중 오류 발생: {str(e)}")
    

@app.post("/v1/documents/delete")
async def delete_document(
    document_resource_name: str = Form(..., description="삭제할 문서의 Resource Name (예: fileSearchStores/.../documents/...)")
):
    """지정된 문서를 Store에서 영구적으로 삭제합니다."""
    
    try:
        # 1. 서비스 레이어의 delete_file 호출
        file_service.delete_file(document_resource_name)
        
        return {
            "status": "success",
            "message": "문서가 성공적으로 삭제되었습니다.",
            "resource_name": document_resource_name
        }
        
    except AttributeError as ae:
        # SDK 버전 호환성 에러 발생 시
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SDK 호환성 오류: {str(ae)}"
        )
    except Exception as e:
        # 문서가 이미 삭제되었거나 경로가 잘못된 경우 등
        # 상세 에러 메시지가 'not found'를 포함하면 404를 반환하도록 처리 가능
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="삭제하려는 문서를 찾을 수 없습니다."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 삭제 중 오류 발생: {str(e)}"
        )

# ---------------------------------------------------------
# [3] AI 질의응답(RAG) 엔드포인트
# ---------------------------------------------------------

