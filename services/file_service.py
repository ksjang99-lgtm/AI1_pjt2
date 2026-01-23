import os
import time
import tempfile
from typing import List, Dict, Any, Iterable
from .gemini_client import get_client


client = get_client()
COMPANY = "starbill"

def upload_to_store(store_name: str, uploaded_file, scope_value: str) -> None:
    """
    업로드 + 인덱싱 완료까지 대기
    """
    original_filename = uploaded_file.name
    suffix = os.path.splitext(original_filename)[1] or ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    config = {
        "display_name": original_filename,
        # ✅ value 대신 string_value 사용
        "custom_metadata": build_custom_metadata(COMPANY, scope_value),
    }

    op = client.file_search_stores.upload_to_file_search_store(
        file=tmp_path,
        file_search_store_name=store_name,
        config=config,
    )

    while not op.done:
        time.sleep(2)
        op = client.operations.get(op)

def build_custom_metadata(company: str, scope: str) -> List[Dict[str, Any]]:
    """
    ✅ [중요] 네 SDK에서는 custom_metadata가 list이며,
    각 원소는 value가 아니라 string_value / numeric_value 등을 사용해야 함.
    (value 필드는 extra_forbidden 에러 발생)
    """
    return [
        {"key": "company", "string_value": company},
        {"key": "scope", "string_value": scope},
    ]




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


def delete_file(document_resource_name: str):
    """특정 문서 삭제"""
    return client.file_search_stores.documents.delete(name=document_resource_name)