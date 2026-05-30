"""Daily report service — 日报生成。"""

import json

from app.core.agent_factory import create_chat_agent
from app.db.app_meta import AppMetaRepository


class DailyReportService:
    def __init__(self, session_repo: AppMetaRepository, db_path: str):
        self.session_repo = session_repo
        self.db_path = db_path

    async def generate(self, target_date: str) -> str | None:
        """生成指定日期的日报。"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # 获取当天活跃的会话
        sessions = self.session_repo.list_sessions()
        transcripts = []

        agent = create_chat_agent()
        for s in sessions:
            try:
                session = agent.get_session(session_id=s["session_id"])
                if session and hasattr(session, "runs"):
                    for run in (session.runs or []):
                        if hasattr(run, "created_at") and target_date in str(run.created_at):
                            transcripts.append({
                                "session_id": s["session_id"],
                                "mode": s["mode"],
                            })
            except Exception:
                continue

        if not transcripts:
            conn.close()
            return None

        prompt = f"请根据以下会话摘要生成日报：\n\n{json.dumps(transcripts, ensure_ascii=False)}"

        try:
            response = await agent.arun(message=prompt, session_id=f"report_{target_date}")
            summary = response.content if isinstance(response.content, str) else str(response.content)

            conn.execute(
                """
                INSERT INTO daily_reports (report_date, summary_md, source_sessions_json)
                VALUES (?, ?, ?)
                ON CONFLICT(report_date) DO UPDATE SET
                    summary_md = excluded.summary_md,
                    source_sessions_json = excluded.source_sessions_json
                """,
                (target_date, summary, json.dumps(transcripts, ensure_ascii=False)),
            )
            conn.commit()
            conn.close()
            return summary
        except Exception as e:
            conn.close()
            print(f"[DailyReport] Error: {e}")
            return None
