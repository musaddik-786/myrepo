"""
server.py — L0 Self-Service Agent
──────────────────────────────────────
LangGraph agent that answers a requester's chat turn only from a matched
KB card's reviewed self-service steps, never diagnosis/cause. Ticket
creation itself is out of scope (that is the un-implemented Ticket Intake
& Creation Agent).

Port: 7014
MCP : http://localhost:7900/api/v1/l0_self_service/mcp

Run:
    py -3 server.py
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Annotated, TypedDict

import uvicorn
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("l0_self_service_agent")

MCP_URL = os.getenv("MCP_URL", "http://localhost:7900/api/v1/l0_self_service/mcp")
AGENT_PORT = int(os.getenv("L0_SELF_SERVICE_AGENT_PORT", "7014"))

config_mcp_server = {
    "l0_self_service_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="L0 Self-Service Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def router(state: State):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    if isinstance(last, AIMessage) and last.content:
        if "Continue" in last.content:
            return "tools"
        if "End" in last.content:
            return "End"
    return "End"


SYSTEM_PROMPT = """
You are the L0 Self-Service Agent for an IT ticket platform, chatting
directly with the requester (not an adjuster/agent persona).

The user message you receive is the whole conversation so far, formatted as
one line per turn ("user: ..." / "assistant: ..."), preceded by a line
"Session: <id>". Reconstruct it into a role/content messages array (role is
exactly "user" or "assistant") in the order given.

STEP 1 — Chat
  Call run_l0_chat with that reconstructed messages array and the session id
  from the "Session:" line (reuse it exactly; never invent a new one while
  one is given).
  This only ever answers from a matched KB card's reviewed self_service
  block -- it will never diagnose or explain root cause. If no card
  matches, it will say it can't resolve this and suggest drafting a ticket.

STEP 2 — Record the outcome (only once the conversation has concluded)
  Call record_outcome with the same session_id and one of: "resolved" (bot
  solved it), "ticket_created" (requester needs a human ticket), or leave
  it as "open" by not calling this yet if the conversation is still going.

STEP 3 — Answer with the full result
  Your final message must contain exactly the JSON object run_l0_chat
  returned to you, re-emitted verbatim -- every key it gave you (reply,
  module, steps, ask_for, ticket_draft, verified, resolved_by_bot, unit_id)
  exactly as returned, never paraphrased, dropped, or reformatted, and no
  markdown code fences around it. Actually creating a ticket is NOT
  something this agent does -- ticket_draft is a draft only.

Use get_stats only if asked for deflection-rate numbers (chats,
resolved_without_ticket, tickets_created, deflection_rate).

When done, end your response with "End" on its own line, after the JSON.
"""


def create_graph(model, tools, prompt):
    graph_builder = StateGraph(State)
    llm_with_tools = model.bind_tools(tools)

    async def agent_node(state: State):
        messages = state["messages"]
        all_messages = [SystemMessage(content=prompt)] + messages
        message = await llm_with_tools.ainvoke(all_messages)
        return {"messages": [message]}

    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", router, {"tools": "tools", "End": END})
    graph_builder.add_edge("tools", "agent")
    return graph_builder.compile()


async def get_tools():
    client = MultiServerMCPClient(config_mcp_server)
    tools = await client.get_tools()
    logger.info("Tools loaded from MCP: %s", [t.name for t in tools])
    return tools


async def stream_graph(graph, initial_state, config):
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f"data: {chunk.content}\n\n"

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Starting...\n\n"

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Done\n\n"


@app.post("/chat")
async def chat_stream(request: Request):
    tools = await get_tools()

    model = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    body = await request.json()
    user_message = body.get("message", "I need help with an issue")

    graph = create_graph(model=model, tools=tools, prompt=SYSTEM_PROMPT)

    async def generate():
        start = time.time()
        last_event_at = start
        last_tool = None
        try:
            async for event in stream_graph(
                graph=graph,
                initial_state={"messages": [user_message]},
                config={"recursion_limit": 250},
            ):
                last_event_at = time.time()
                if isinstance(event, str) and event.startswith("data: [Tool:"):
                    try:
                        last_tool = event.split("[Tool:", 1)[1].split("]", 1)[0]
                    except Exception:
                        pass
                yield event
        except BaseException as e:
            elapsed = time.time() - start
            since_last = time.time() - last_event_at
            err = {
                "exception_class": type(e).__name__,
                "message": str(e),
                "elapsed_total_seconds": round(elapsed, 2),
                "seconds_since_last_event": round(since_last, 2),
                "last_tool_invoked": last_tool,
                "traceback": traceback.format_exc(),
                "timestamp_utc": datetime.utcnow().isoformat(),
            }
            logger.error("AGENT_ERROR %s", json.dumps(err, default=str))
            try:
                yield f"data: [AGENT_ERROR] {json.dumps(err, default=str)}\n\n"
            except Exception:
                pass
            import asyncio
            if isinstance(e, asyncio.CancelledError):
                raise

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "l0_self_service_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
