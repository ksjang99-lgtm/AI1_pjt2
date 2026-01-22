import streamlit as st
import os
from services import file_service, gemini_client

# 설정
st.set_page_config(page_title="Starbill Admin - 문서 관리", layout="wide")
st.title("📚 스타빌 조달문서 관리자")

STORE_NAME = gemini_client.get_default_store_name()
SCOPES = {"law": "법령", "rule": "규칙", "sheet": "공고문"}

# 세션 상태 초기화
if "refresh" not in st.session_state:
    st.session_state.refresh = False

# --- 1. 파일 업로드 섹션 ---
st.subheader("파일 업로드")
with st.container(border=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("PDF 또는 텍스트 파일을 선택하세요", type=["pdf", "txt"])
    with col2:
        selected_scope = st.selectbox("문서 카테고리", options=list(SCOPES.keys()), 
                                     format_func=lambda x: SCOPES[x])
    
    if st.button("🚀 업로드 및 인덱싱 시작", data_priority="primary"):
        if uploaded_file:
            with st.spinner("Google Gemini가 문서를 분석하고 인덱싱 중입니다..."):
                # 임시 파일 저장 후 업로드
                with st.named_temporary_file(delete=False, suffix=f"_{uploaded_file.name}") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                try:
                    file_service.upload_to_store(STORE_NAME, tmp_path, uploaded_file.name, selected_scope)
                    st.success(f"✅ '{uploaded_file.name}' 업로드 완료!")
                    st.session_state.refresh = True
                finally:
                    if os.path.exists(tmp_path): os.remove(tmp_path)
        else:
            st.warning("파일을 먼저 선택해주세요.")

st.divider()

# --- 2. 문서 목록 및 삭제 섹션 ---
st.subheader("인덱싱된 문서 현황")
files = file_service.list_files(STORE_NAME)

if not files:
    st.info("현재 등록된 문서가 없습니다.")
else:
    # 테이블 표시
    st.dataframe(files, use_container_width=True, hide_index=True)
    
    # 삭제 인터페이스
    st.subheader("문서 삭제")
    labels = [f"[{f['scope']}] {f['display_name']}" for f in files]
    selected_label = st.selectbox("삭제할 문서를 선택하세요", options=labels)
    
    if st.button("🗑️ 선택한 문서 삭제", type="secondary"):
        target_idx = labels.index(selected_label)
        target_file = files[target_idx]
        
        with st.spinner("삭제 중..."):
            file_service.delete_file(target_file["name"])
            st.success("삭제되었습니다.")
            st.rerun()