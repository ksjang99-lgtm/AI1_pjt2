from pydantic import BaseModel
from typing import Optional

# 클라이언트가 보낼 데이터 구조 정의
class ChatRequest(BaseModel):
    buy_type: str            # 입찰/견적
    procurement_type: str    # 물품/용역/공사
    estimated_price: str     # 추정가격
    tax: str                 # 과세/면세
    procurement_gsc: str     # 물품명 등
    competition_method: str  # 경쟁방식
    rec_startdate: str       # 신청시작일
    prompt: str              # 실제 질문 내용
    

# 2. 내부 로직용 (1번을 상속받아 비밀 필드 추가)
class InternalChatQuery(ChatRequest):
    temperature: Optional[float] = 0.0