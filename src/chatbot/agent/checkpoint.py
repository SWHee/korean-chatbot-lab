"""로컬 Agent 대화 상태 저장소"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHECKPOINT_PATH = PROJECT_ROOT / ".runtime" / "langgraph.sqlite3"


def create_sqlite_checkpointer(
    *,
    database_path: Path = DEFAULT_CHECKPOINT_PATH,
) -> SqliteSaver:
    """SQLite 파일에 Agent 상태를 저장하는 Checkpointer 생성"""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    return SqliteSaver(connection)
