# pip install streamlit python-dotenv google-genai

import os
import time
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterable

import streamlit as st
from dotenv import load_dotenv
from google import genai


# ---------------------------------
# Page
# ---------------------------------
st.set_page_config(page_title="Starbill File Search Admin", layout="wide")
st.title("📚 Starbill - Google File Search 관리자")


# ---------------------------------
# Env / Constants
# ---------------------------------
load_dotenv()

API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
ENV_STORE_NAME = (os.getenv("FILE_SEARCH_STORE_NAME") or "").strip()

COMPANY = "starbill"
SCOPES = ["law", "rule", "sheet"]
SCOPE_LABEL = {"law": "법령", "rule": "규칙", "sheet": "공고문"}

if not API_KEY:
    st.error("`.env`에 GEMINI_API_KEY를 설정하세요.")
    st.stop()

client = genai.Client(api_key=API_KEY)


# ---------------------------------
# Session State init (✅ .env 자동 세팅)
# ---------------------------------
if "store_name" not in st.session_state:
    st.session_state.store_name = ENV_STORE_NAME  # ✅ 페이지 로드 시 env에서 자동 세팅
if "last_created_store" not in st.session_state:
    st.session_state.last_created_store = ""


# ---------------------------------
# Helpers
# ---------------------------------
def safe_get(obj: Any, attr: str, default=None):
    try:
        return getattr(obj, attr)
    except Exception:
        return default


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


def normalize_meta_from_any(meta: Any) -> Dict[str, str]:
    """
    custom_metadata가 SDK 버전에 따라
    - dict 형태
    - list 형태([{key,string_value}...])
    - 객체 리스트 형태
    등으로 올 수 있어 모두 dict로 정규화
    """
    if meta is None:
        return {}

    # 1) dict 형태 (드물지만 방어)
    if isinstance(meta, dict):
        return {str(k): str(v) for k, v in meta.items()}

    # 2) list 형태: [{"key":"company","string_value":"starbill"}, ...]
    if isinstance(meta, list):
        out: Dict[str, str] = {}
        for item in meta:
            if isinstance(item, dict):
                k = item.get("key") or item.get("name") or item.get("field")
                # ✅ string_value 우선, 그 외 타입도 일부 수용
                v = (
                    item.get("string_value")
                    or item.get("value")
                    or item.get("val")
                    or item.get("numeric_value")
                )
                if k is not None and v is not None:
                    out[str(k)] = str(v)
            else:
                k = safe_get(item, "key", None) or safe_get(item, "name", None)
                v = (
                    safe_get(item, "string_value", None)
                    or safe_get(item, "value", None)
                    or safe_get(item, "numeric_value", None)
                )
                if k is not None and v is not None:
                    out[str(k)] = str(v)
        return out

    # 3) 그 외 형태 변환 시도
    try:
        d = dict(meta)
        return {str(k): str(v) for k, v in d.items()}
    except Exception:
        return {}


def get_doc_custom_metadata(doc_obj: Any) -> Dict[str, str]:
    meta = safe_get(doc_obj, "custom_metadata", None)
    return normalize_meta_from_any(meta)


def iter_store_documents(store_name: str) -> Iterable[Any]:
    """
    ✅ SDK 차이를 흡수하는 문서 목록 iterator
    - 네 환경에서는 file_search_stores.list_files가 없으므로 documents.list(...) 사용
    """
    docs_service = safe_get(client.file_search_stores, "documents", None)
    if docs_service is None:
        raise AttributeError("client.file_search_stores.documents 가 없습니다. SDK 버전을 확인하세요.")

    list_fn = safe_get(docs_service, "list", None)
    if list_fn is None:
        raise AttributeError("client.file_search_stores.documents.list 가 없습니다. SDK 버전을 확인하세요.")

    # 시그니처 차이 흡수: parent 키워드/포지셔널 둘 다 시도
    try:
        pager = list_fn(parent=store_name)
    except TypeError:
        pager = list_fn(store_name)

    for item in pager:
        yield item


def fetch_company_files(store_name: str, company: str) -> List[Dict[str, str]]:
    """
    Store 내 문서(Document) 목록 중 custom_metadata.company == company 만 반환
    반환: display_name / name(document resource) / scope
    """
    rows: List[Dict[str, str]] = []

    for doc in iter_store_documents(store_name):
        meta = get_doc_custom_metadata(doc)
        if meta.get("company") != company:
            continue

        rows.append(
            {
                "display_name": str(safe_get(doc, "display_name", "")),
                "name": str(safe_get(doc, "name", "")),  # 예: fileSearchStores/.../documents/...
                "scope": meta.get("scope", ""),
            }
        )

    rows.sort(key=lambda x: (x["scope"], x["display_name"], x["name"]))
    return rows


def delete_document(document_resource_name: str) -> None:
    docs_service = safe_get(client.file_search_stores, "documents", None)
    if docs_service is None:
        raise AttributeError("client.file_search_stores.documents 가 없습니다. SDK 버전을 확인하세요.")

    delete_fn = safe_get(docs_service, "delete", None)
    if delete_fn is None:
        raise AttributeError("client.file_search_stores.documents.delete 가 없습니다. SDK 버전을 확인하세요.")

    try:
        delete_fn(name=document_resource_name, force=True)
    except TypeError:
        # SDK 버전에 따라 인자 형태가 다를 수 있어 fallback
        try:
            delete_fn(document_resource_name, force=True)
        except TypeError:
            # 또 다른 버전 형태: config 딕셔너리
            delete_fn(name=document_resource_name, config={"force": True})


def delete_existing_same_filename(
    store_name: str,
    company: str,
    filename: str,
    scope: Optional[str] = None,
) -> int:
    """
    company=starbill 이면서 display_name==filename 인 기존 문서 삭제.
    - scope 지정 시 해당 scope만 삭제
    - scope=None이면 scope 상관없이 모두 삭제 (파일명 기준 전체 교체)
    """
    rows = fetch_company_files(store_name, company)
    targets = []
    for r in rows:
        if r["display_name"] != filename:
            continue
        if scope is not None and r.get("scope") != scope:
            continue
        targets.append(r["name"])

    for doc_name in targets:
        delete_document(doc_name)

    return len(targets)


def upload_file(store_name: str, uploaded_file, scope_value: str) -> None:
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


def create_store(display_name: str) -> str:
    store = client.file_search_stores.create(config={"display_name": display_name})
    return store.name


# ---------------------------------
# Store Setup
# ---------------------------------
st.subheader("0) Store 설정/생성")

with st.expander("Store 생성 / 설정", expanded=True):
    st.write("**company(고정):**")
    st.code(COMPANY)

    st.write("**.env에서 읽은 FILE_SEARCH_STORE_NAME:**")
    st.code(ENV_STORE_NAME if ENV_STORE_NAME else "(비어있음)")

    col_s1, col_s2 = st.columns([2, 3], vertical_alignment="center")

    with col_s1:
        new_store_display_name = st.text_input(
            "새 Store display_name",
            value=f"starbill-store-{datetime.now().strftime('%Y%m%d')}",
        ).strip()

    with col_s2:
        if st.button("➕ 새 Store 만들기", type="primary"):
            try:
                with st.spinner("Store 생성 중..."):
                    created = create_store(new_store_display_name or "starbill-main-store")
                st.session_state.last_created_store = created
                st.session_state.store_name = created
                st.success("✅ Store 생성 완료")
            except Exception as e:
                st.exception(e)

    if st.session_state.last_created_store:
        st.info("생성된 Store name을 `.env`에 저장하세요(앱 재시작 시 자동 로드).")
        st.code(st.session_state.last_created_store)
        st.code(f"FILE_SEARCH_STORE_NAME={st.session_state.last_created_store}", language="bash")

st.divider()

# ---------------------------------
# Store 선택(입력)
# ---------------------------------
st.subheader("1) 사용할 Store")

store_name = st.text_input(
    "Store name (fileSearchStores/...)",
    value=st.session_state.store_name,
    placeholder="fileSearchStores/xxxxxxxx",
    help="기본값은 .env의 FILE_SEARCH_STORE_NAME입니다. 필요하면 여기서 바꿀 수 있습니다.",
).strip()
st.session_state.store_name = store_name

if not store_name:
    st.warning("Store name이 비어 있습니다. `.env`에 FILE_SEARCH_STORE_NAME을 설정하거나 위에서 Store를 생성하세요.")
    st.stop()

st.caption(f"현재 선택된 Store: **{store_name}**")

st.divider()

# ---------------------------------
# Upload UI
# ---------------------------------
st.subheader("2) 문서 업로드")

scope = st.radio(
    "scope 선택",
    options=SCOPES,
    format_func=lambda x: f"{SCOPE_LABEL.get(x, x)} ({x})",
    horizontal=True,
)

uploaded = st.file_uploader("업로드할 파일 선택", type=None)

col_u1, col_u2, col_u3 = st.columns([1, 1, 3], vertical_alignment="center")
do_upload = col_u1.button("🚀 업로드", type="primary", disabled=(uploaded is None))
do_overwrite = col_u2.button("🔁 갱신(동일 파일명 교체)", disabled=(uploaded is None))

with col_u3:
    if uploaded is not None:
        st.caption(
            f"display_name: **{uploaded.name}** / company: **{COMPANY}** / scope: **{scope}**"
        )

overwrite_scope_only = st.checkbox("갱신 시 동일 scope만 교체", value=False)

if uploaded is not None and (do_upload or do_overwrite):
    try:
        if do_overwrite:
            with st.spinner("기존 동일 파일명 문서 삭제 중..."):
                deleted_count = delete_existing_same_filename(
                    store_name,
                    COMPANY,
                    uploaded.name,
                    scope=(scope if overwrite_scope_only else None),
                )
            st.info(f"기존 문서 {deleted_count}건 삭제 완료 (동일 파일명 기준).")

        with st.spinner("업로드 및 인덱싱 중..."):
            upload_file(store_name, uploaded, scope)

        st.success("✅ 업로드 & 인덱싱 완료")
        st.rerun()

    except Exception as e:
        st.exception(e)

st.divider()

# ---------------------------------
# List / Filter / Delete UI
# ---------------------------------
st.subheader("3) 문서 목록/관리 (company=starbill)")

col_r1, col_r2 = st.columns([1, 3], vertical_alignment="center")
with col_r1:
    if st.button("🔄 재조회"):
        st.rerun()
with col_r2:
    st.caption("화면 로드 시 자동 조회되며, 업로드/삭제 후에도 자동 갱신됩니다.")

try:
    all_rows = fetch_company_files(store_name, COMPANY)
except Exception as e:
    st.exception(e)
    st.stop()

tabs = st.tabs(["전체", "법령(law)", "규칙(rule)", "공고문(sheet)"])

def render_table(rows: List[Dict[str, str]], key_prefix: str):
    if not rows:
        st.info("문서가 없습니다.")
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "display_name": st.column_config.TextColumn("display_name"),
            "name": st.column_config.TextColumn("name (document id)"),
            "scope": st.column_config.TextColumn("scope"),
        },
    )

    st.subheader("선택 후 삭제")
    labels = [f"[{r['scope']}] {r['display_name']}  |  {r['name']}" for r in rows]
    selected = st.selectbox("삭제할 문서 선택", options=labels, key=f"{key_prefix}_sel")
    idx = labels.index(selected)
    doc_name = rows[idx]["name"]

    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    confirm = c1.checkbox("삭제 확인", value=False, key=f"{key_prefix}_confirm")
    c2.caption("삭제는 되돌릴 수 없습니다. 삭제 후 목록이 자동 갱신됩니다.")

    if st.button("🗑️ 선택 문서 삭제", disabled=not confirm, key=f"{key_prefix}_delbtn"):
        try:
            with st.spinner("삭제 중..."):
                delete_document(doc_name)
            st.success("✅ 삭제 완료")
            st.rerun()
        except Exception as e:
            st.exception(e)

with tabs[0]:
    render_table(all_rows, "all")

with tabs[1]:
    render_table([r for r in all_rows if r.get("scope") == "law"], "law")

with tabs[2]:
    render_table([r for r in all_rows if r.get("scope") == "rule"], "rule")

with tabs[3]:
    render_table([r for r in all_rows if r.get("scope") == "sheet"], "sheet")
