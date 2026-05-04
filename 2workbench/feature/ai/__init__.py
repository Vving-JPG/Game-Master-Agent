# 2workbench/feature/ai/__init__.py
"""AI 编排层 — LangGraph Agent 核心"""
from feature.ai.graph import gm_graph, build_gm_graph
from feature.ai.graph_compiler import graph_compiler
from feature.ai.gm_agent import GMAgent
from feature.ai.agent_runner import agent_runner, AgentRunner
from feature.ai.nodes import (
    node_handle_event, node_build_prompt, node_llm_reasoning,
    node_parse_output, node_execute_commands, node_update_memory,
)
from feature.ai.command_parser import parse_llm_output, ParsedOutput, ParsedCommand
from feature.ai.prompt_builder import PromptBuilder
from feature.ai.skill_loader import SkillLoader, Skill, SkillMetadata
from feature.ai.tools import ALL_TOOLS, get_tools_schema
from feature.ai.events import (
    TURN_START, TURN_END, AGENT_ERROR,
    LLM_STREAM_TOKEN, LLM_STREAM_REASONING,
    COMMAND_PARSED, COMMAND_EXECUTED, MEMORY_STORED,
    create_turn_start_event, create_turn_end_event, create_stream_token_event,
)

__all__ = [
    "gm_graph", "build_gm_graph", "graph_compiler", "GMAgent",
    "agent_runner", "AgentRunner",
    "parse_llm_output", "PromptBuilder", "SkillLoader",
    "ALL_TOOLS", "get_tools_schema",
]
