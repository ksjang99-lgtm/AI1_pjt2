import streamlit as st
from services import rag_service, gemini_client

# 설정
APP_TITLE = "스타빌 조달문서 AI 어시스턴트"
st.set_page_config(page_title=APP_TITLE, layout="centered")
st.title(f"🤖 {APP_TITLE}")

STORE_NAME = gemini_client.get_default_store_name()

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 사이드바 설정 ---
with st.sidebar:
    st.header("설정")
    model_name = st.selectbox("모델 선택", ["gemini-2.0-flash-exp", "gemini-1.5-flash"])
    temp = st.slider("창의성(Temperature)", 0.0, 1.0, 0.0, 0.1)
    if st.button("대화 기록 삭제"):
        st.session_state.messages = []
        st.rerun()

# --- 채팅 인터페이스 ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("국가계약법상 입찰 공고 기간은 어떻게 되나요?"):
    # 유저 메시지 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("문서에서 근거를 찾는 중..."):
            try:
                result = rag_service.query_rag(
                    user_query=prompt,
                    store_name=STORE_NAME,
                    model=model_name,
                    temperature=temp
                )
                answer = result["answer"]
                st.markdown(answer)
                
                # 응답 저장
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")