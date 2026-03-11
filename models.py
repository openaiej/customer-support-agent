from pydantic import BaseModel
from typing import Optional


class UserAccountContext(BaseModel):

    customer_id: int
    name: str
    tier: str = "basic"
    email: Optional[str] = None  # premium entreprise


class InputGuardRailOutput(BaseModel):
    """Input Guardrail 검사 결과 - 주제 이탈 + 부적절 메시지 필터"""

    is_off_topic: bool
    is_inappropriate: bool  # 욕설, 비방, 성적 발언 등
    reason: str


class OutputGuardRailOutput(BaseModel):
    """Output Guardrail 검사 결과 - 봇 응답의 부적절 여부"""

    is_inappropriate: bool
    reason: str


class HandoffData(BaseModel):

    to_agent_name: str
    issue_type: str
    issue_description: str
    reason: str