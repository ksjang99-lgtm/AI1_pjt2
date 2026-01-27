from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class Section(BaseModel):
    title: str = Field(..., description="섹션 제목")
    items: List[str] = Field(..., description="상세 항목 리스트")
    model_config = ConfigDict(extra="forbid")

class BiddingNoticeResponse(BaseModel):
    # 모든 응답을 'title'과 'items'를 가진 객체들의 리스트로 구성
    sections: List[Section] = Field(..., description="입찰공고 전체 섹션")
    model_config = ConfigDict(extra="forbid")

# 클라이언트가 보낼 데이터 구조 정의
class ChatRequest(BaseModel):
    buy_type: str            # 입찰/견적
    procurement_type: str    # 물품/용역/공사
    estimated_price: str     # 추정가격
    tax: str                 # 과세/면세
    procurement_gsc: str     # 물품명 등
    competition_method: str  # 경쟁방식
    rec_startdate: date       # 입찰참가신청 시작일
    prompt: str              # 실제 질문 내용
    

# 2. 내부 로직용 (1번을 상속받아 비밀 필드 추가)
class InternalChatQuery(ChatRequest):
    temperature: Optional[float] = 0.0