"""Agent 개발 Dataset의 로컬 계약"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_DATASET_VERSION = "agent-v1-dev"
FINLIFE_FIXTURE_VERSION = "finlife-deposit-v1"
AGENT_DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "agent-v1-dev.jsonl"
FINLIFE_FIXTURE_PATH = (
    PROJECT_ROOT / "data" / "evaluation" / "finlife-deposit-v1.json"
)

AgentCategory = Literal["law", "product", "mixed", "boundary"]
ExpectedRoute = Literal["ready", "clarify", "out_of_scope"]
ExpectedToolName = Literal[
    "search_law_articles",
    "search_financial_products",
]
ExpectedToolStatus = Literal["ok", "no_match", "unsupported", "error"]


class ExpectedTool(BaseModel):
    """한 턴에서 기대하는 Tool 호출과 결과 상태"""

    model_config = ConfigDict(extra="forbid")

    name: ExpectedToolName
    arguments: dict[str, object] = Field(default_factory=dict)
    expected_status: ExpectedToolStatus | None = None


class AgentEvaluationTurn(BaseModel):
    """사용자 메시지 한 턴의 기대 행동"""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    expected_route: ExpectedRoute
    expected_tools: list[ExpectedTool] = Field(default_factory=list)
    expected_missing_fields: list[str] = Field(default_factory=list)
    expected_behavior: str = Field(min_length=1)


class AgentEvaluationCase(BaseModel):
    """단일 또는 두 턴 Agent 평가 사례"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^(L|P|M|B)\d{2}$")
    dataset_version: str
    split: Literal["dev"]
    category: AgentCategory
    turns: list[AgentEvaluationTurn] = Field(min_length=1, max_length=2)
    finlife_fixture_version: str | None = None

    @model_validator(mode="after")
    def validate_trajectory_contract(self):
        """두 턴 clarify 흐름과 상품 fixture 연결 확인"""
        if len(self.turns) == 2:
            if self.turns[0].expected_route != "clarify":
                raise ValueError("two-turn case must start with clarify")
            if self.turns[1].expected_route != "ready":
                raise ValueError("two-turn case must finish with ready")

        uses_product_tool = any(
            tool.name == "search_financial_products"
            for turn in self.turns
            for tool in turn.expected_tools
        )
        if uses_product_tool and self.finlife_fixture_version != FINLIFE_FIXTURE_VERSION:
            raise ValueError("product tool case requires fixed Finlife fixture")
        return self


def load_agent_evaluation_cases(
    path: Path = AGENT_DATASET_PATH,
) -> list[AgentEvaluationCase]:
    """JSONL Agent 개발 사례 로드와 중복 ID 검증"""
    cases = [
        AgentEvaluationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    case_ids = [case.id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("agent dataset contains duplicate case IDs")
    return cases


def load_finlife_fixture(
    path: Path = FINLIFE_FIXTURE_PATH,
) -> dict:
    """상품 Tool 평가용 고정 Finlife 응답 로드"""
    return json.loads(path.read_text(encoding="utf-8"))
