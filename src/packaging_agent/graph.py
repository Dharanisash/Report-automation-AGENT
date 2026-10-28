"""LangGraph state machine definition and compilation."""

import os
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode

from packaging_agent.config import settings
from packaging_agent.db import init_db
from packaging_agent.prompts import SYSTEM_PROMPT
from packaging_agent.tools import ALL_TOOLS


class AgentState(TypedDict):
    """Agent state tracking conversation history and tool outputs."""

    messages: Annotated[List[BaseMessage], "Conversation history and agent scratchpad"]


def create_packaging_agent(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    db_path: Optional[str] = None,
):
    """Compiles the autonomous LangGraph packaging reporting agent."""
    active_db = db_path or settings.db_path
    init_db(active_db)

    active_api_key = api_key or os.getenv("OPENAI_API_KEY", "") or settings.openai_api_key
    if not active_api_key:
        active_api_key = "placeholder-key-for-local-graph-init"

    active_model = model_name or settings.openai_model
    llm = ChatOpenAI(
        model=active_model,
        temperature=settings.temperature,
        api_key=active_api_key,
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState) -> AgentState:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(ALL_TOOLS)

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", "__end__"])
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def run_agent_cycle(
    prompt: str = "Execute today's packaging deployment reporting lifecycle.",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs a full autonomous execution cycle."""
    agent = create_packaging_agent(model_name=model_name, api_key=api_key)
    result = agent.invoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        }
    )
    return result
