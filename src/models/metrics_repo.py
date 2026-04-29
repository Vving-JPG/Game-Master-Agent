"""AI 行为指标数据访问"""
import json
from src.services.database import get_db


def record_llm_call(world_id: int, call_type: str = "chat",
                     prompt_tokens: int = 0, completion_tokens: int = 0,
                     latency_ms: int = 0, tool_calls_count: int = 0,
                     tool_names: list | None = None, error: str = "",
                     db_path: str | None = None) -> int:
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO llm_calls
               (world_id, call_type, prompt_tokens, completion_tokens, total_tokens,
                latency_ms, tool_calls_count, tool_names, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (world_id, call_type, prompt_tokens, completion_tokens,
             prompt_tokens + completion_tokens, latency_ms, tool_calls_count,
             json.dumps(tool_names or []), error),
        )
        return cursor.lastrowid


def get_recent_calls(world_id: int | None = None, limit: int = 50,
                     db_path: str | None = None) -> list[dict]:
    with get_db(db_path) as conn:
        if world_id:
            rows = conn.execute(
                "SELECT * FROM llm_calls WHERE world_id = ? ORDER BY created_at DESC LIMIT ?",
                (world_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM llm_calls ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_token_stats(db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_calls,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt,
                COALESCE(SUM(completion_tokens), 0) as total_completion,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(AVG(latency_ms), 0) as avg_latency,
                COALESCE(SUM(CASE WHEN error != '' THEN 1 ELSE 0 END), 0) as error_count
            FROM llm_calls
        """).fetchone()
    return dict(row)
