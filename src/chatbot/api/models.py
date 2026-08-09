"""FastAPI 요청·응답 Pydantic 모델"""

from pydantic import BaseModel, Field

from chatbot.finlife import FinancialProductOption


class RagRequest(BaseModel):
    """법령 RAG에 전달할 사용자 질문 검증"""

    question: str = Field(min_length=1)


class RagSource(BaseModel):
    """RAG 답변에 사용한 법령 근거"""

    law_name: str
    article_no: str
    effective_date: str
    similarity: float


class RagResponse(BaseModel):
    """법령 RAG 답변과 검색 근거 형식 정의"""

    response: str
    sources: list[RagSource]
    generation_seconds: float


class AgentRequest(BaseModel):
    """멀티턴 Agent에 전달할 thread와 현재 사용자 메시지"""

    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class AgentSource(BaseModel):
    """Agent 법령 Tool이 반환한 인용 근거"""

    source_id: str
    law_name: str
    article_no: str
    effective_date: str


class AgentToolResult(BaseModel):
    """한 번의 Agent Tool 호출과 결과 상태"""

    name: str
    arguments: dict[str, object]
    status: str | None = None


class AgentResponse(BaseModel):
    """멀티턴 Agent의 답변과 실행 요약"""

    thread_id: str
    answer: str
    route: str
    product_preferences: dict[str, object] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    tools: list[AgentToolResult]
    sources: list[AgentSource]
    products: list[FinancialProductOption]
    execution_seconds: float
