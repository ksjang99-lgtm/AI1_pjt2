import os
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------
# App Title (요청 1)
# ---------------------------
APP_TITLE = "스타빌 조달문서 생성형 AI 어시스턴트 (파일검색 기반)"  # <- “스타빌 입찰공고서 작성기(안)” 취지를 반영해 더 그럴듯하게

# ---------------------------
# Env
# ---------------------------
load_dotenv()
API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
STORE_NAME = (os.getenv("FILE_SEARCH_STORE_NAME") or "").strip()

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY가 .env에 없습니다.")
if not STORE_NAME:
    raise RuntimeError("FILE_SEARCH_STORE_NAME가 .env에 없습니다.")

client = genai.Client(api_key=API_KEY)

# ---------------------------
# Page
# ---------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# ---------------------------
# Store info (요청 3)
# ---------------------------
@st.cache_data(ttl=60)
def get_store_display_name(store_name: str) -> str:
    """
    File Search Store의 display_name 조회
    (공식 문서: client.file_search_stores.get(name=...) 사용) :contentReference[oaicite:1]{index=1}
    """
    store = client.file_search_stores.get(name=store_name)
    dn = getattr(store, "display_name", None)
    return dn or "(display_name 없음)"

store_display_name = get_store_display_name(STORE_NAME)

info_col1, info_col2 = st.columns([1, 2], vertical_alignment="center")
with info_col1:
    st.caption("현재 연결된 File Search Store")
with info_col2:
    st.code(f"STORE_NAME: {STORE_NAME}\nDISPLAY_NAME: {store_display_name}")

# ---------------------------
# Sidebar: Customizable controls (요청 2)
# ---------------------------
with st.sidebar:
    st.header("⚙️ 설정/컨트롤 (확장용)")
    st.caption("추후 '입찰공고 작성 컨트롤', '출력 형식', '템플릿 선택' 등을 여기에 추가하면 됩니다.")

    model = st.selectbox(
        "모델",
        options=[
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-2.5-pro",
            "gemini-3-flash-preview-lite",
        ],
        index=0,
        help="File Search 지원 모델 목록은 공식 문서 참고. :contentReference[oaicite:2]{index=2}",
    )
    temperature = st.slider("temperature", 0.0, 1.0, 0.0, 0.05)
    max_tokens = st.slider("max_output_tokens", 128, 4096, 1024, 64)

    st.divider()
    show_debug = st.checkbox("디버그(원본 응답/메타데이터) 보기", value=False)
    st.caption("File Search는 다른 도구(예: Google Search)와 함께 사용 불가입니다. :contentReference[oaicite:3]{index=3}")

# ---------------------------
# System instruction (요청 4)
# ---------------------------
SYSTEM_INSTRUCTION = """
당신은 '스타빌 조달문서 도우미'이다.
절대 규칙:
1) 반드시 제공된 File Search store에서 검색된 근거(문서 내용)로만 답하라.
2) File Search 결과/근거가 없으면 "문서에서 확인할 수 없습니다."라고 답하라.
3) 추측/상상/일반지식으로 보완하지 말라.
4) 사용자의 질문이 문서 범위를 벗어나면, 문서에 추가로 어떤 정보가 필요할지 짧게 안내하라.
"""

# ---------------------------
# Chat state
# ---------------------------
if "messages" not in st.session_state:
    # 확장성을 위해 role/content 외에 meta 필드도 함께 저장
    st.session_state.messages: List[Dict[str, Any]] = [
        {
            "role": "assistant",
            "content": "안녕하세요. 업로드된 문서(File Search) 안에서만 근거를 찾아 답변합니다. 무엇을 도와드릴까요?",
            "meta": {"type": "greeting"},
        }
    ]

# ---------------------------
# Layout: Left = chat, Right = panels
# ---------------------------
chat_col, panel_col = st.columns([3, 2], gap="large")

with panel_col:
    st.subheader("🧩 상태/패널 (확장 영역)")
    with st.expander("현재 정책(요약)", expanded=True):
        st.write("- 답변은 **File Search store 내부 근거로만** 생성")
        st.write("- 근거가 없으면 **'문서에서 확인할 수 없습니다.'**")
        st.write("- 외부 검색/상상 금지")

    with st.expander("향후 추가할 수 있는 것들", expanded=False):
        st.write("- 공고문 템플릿 선택 (학교/기관별)")
        st.write("- 출력 포맷(JSON/Markdown/한글 스타일)")
        st.write("- 필수 입력 체크리스트")
        st.write("- 메타데이터 필터(scope=law/rule/sheet) 기반 검색 범위 제한")

# ---------------------------
# Render chat messages
# ---------------------------
with chat_col:
    st.subheader("💬 문서 기반 채팅")

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if show_debug and m.get("meta"):
                with st.expander("debug(meta)", expanded=False):
                    st.json(m["meta"])

    user_text = st.chat_input("질문을 입력하세요 (문서 기반 검색)")

# ---------------------------
# Call Gemini with File Search Tool
# ---------------------------
def ask_with_file_search(user_query: str) -> Dict[str, Any]:
    """
    File Search store를 tool로 붙여서 generate_content 호출
    (공식 예시: types.Tool(file_search=types.FileSearch(...)) ) :contentReference[oaicite:4]{index=4}
    """
    tool = types.Tool(
        file_search=types.FileSearch(
            file_search_store_names=[STORE_NAME]
        )
    )

    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[tool],
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    resp = client.models.generate_content(
        model=model,
        contents=user_query,
        config=cfg,
    )

    # 가능한 한 안전하게 텍스트/메타를 추출
    out_text = getattr(resp, "text", None) or ""
    meta: Dict[str, Any] = {}

    # candidates/grounding 등은 SDK 버전별 구조가 달라질 수 있어 방어적으로 저장
    try:
        meta["raw_response_type"] = str(type(resp))
        if hasattr(resp, "candidates"):
            meta["candidates_len"] = len(resp.candidates) if resp.candidates else 0
    except Exception:
        pass

    # 원본을 그대로 저장하면 너무 커질 수 있어, 디버그 토글에서만 최소 정보만
    return {"text": out_text.strip(), "meta": meta}


# ---------------------------
# Handle user input
# ---------------------------
if user_text:
    # 1) Add user msg
    st.session_state.messages.append({"role": "user", "content": user_text, "meta": {}})

    # 2) Generate assistant msg
    with chat_col:
        with st.chat_message("assistant"):
            with st.spinner("문서에서 근거를 찾는 중..."):
                result = ask_with_file_search(user_text)

            answer = result["text"] or "문서에서 확인할 수 없습니다."
            st.markdown(answer)

            if show_debug:
                with st.expander("debug(meta)", expanded=False):
                    st.json(result.get("meta", {}))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "meta": result.get("meta", {})}
    )
    st.rerun()
