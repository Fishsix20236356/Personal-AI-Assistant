"""Agent factory — 创建各模式的 Agent 实例。"""

from agno.agent import Agent

from app.core.agno_db import build_agno_db
from app.core.model_factory import build_model
from app.core.prompt_templates import (
    CHAT_INSTRUCTIONS,
    WECHAT_INSTRUCTIONS,
    SOP_INSTRUCTIONS,
)
from config.settings import settings


def create_chat_agent(model=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=CHAT_INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=3,
        read_chat_history=False,
        search_session_history=False,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        retries=2,
        delay_between_retries=1,
    )


def create_wechat_agent(model=None, tools=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=WECHAT_INSTRUCTIONS,
        tools=tools or [],
        add_history_to_context=True,
        num_history_runs=2,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        tool_call_limit=6,
        retries=2,
        delay_between_retries=1,
    )


def create_sop_agent(model=None, tools=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=SOP_INSTRUCTIONS,
        tools=tools or [],
        add_history_to_context=True,
        num_history_runs=3,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        tool_call_limit=8,
        retries=2,
        delay_between_retries=1,
    )
