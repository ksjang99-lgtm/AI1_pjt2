import os
import time
import tempfile
from typing import List, Dict, Any, Iterable
from .gemini_client import get_client

client = get_client()
COMPANY = "starbill"

def normalize_meta(meta: Any) -> Dict[str, str]:
    """SDK 버전별로 다른 메타데이터 구조를 dict로 정규화"""
    if meta is None: return {}
    if isinstance(meta, dict): return {str(k): str(v) for k, v in meta.items()}
    
    out = {}
    if isinstance(meta, list):
        for item in meta:
            k = getattr(item, 'key', None) or item.get('key')
            v = getattr(item, 'string_value', None) or item.get('string_value')
            if k and v: out[str(k)] = str(v)
    return out

def list_files(store_name: str, scope: str = None) -> List[Dict[str, str]]:
    """Store 내 문서 목록 조회 및 필터링"""
    rows = []
    # SDK 구조에 맞게 documents.list 호출
    pager = client.file_search_stores.documents.list(parent=store_name)
    
    for doc in pager:
        meta = normalize_meta(getattr(doc, "custom_metadata", None))
        if meta.get("company") != COMPANY:
            continue
        if scope and meta.get("scope") != scope:
            continue
            
        rows.append({
            "display_name": getattr(doc, "display_name", ""),
            "name": getattr(doc, "name", ""), # document resource name
            "scope": meta.get("scope", "")
        })
    return rows

def upload_to_store(store_name: str, file_path: str, filename: str, scope: str):
    """파일 업로드 및 인덱싱 완료 대기"""
    config = {
        "display_name": filename,
        "custom_metadata": [
            {"key": "company", "string_value": COMPANY},
            {"key": "scope", "string_value": scope},
        ],
    }
    
    # 업로드 실행
    op = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        config=config,
    )
    
    # 인덱싱 완료 대기
    while not op.done:
        time.sleep(2)
        op = client.operations.get(op)
    return op.result

def delete_file(document_resource_name: str):
    """특정 문서 삭제"""
    return client.file_search_stores.documents.delete(name=document_resource_name)