"""
server.py — Knowledge Ingestion & Curation Agent
──────────────────────────────────────────────────
LangGraph agent that refreshes the Knowledge Store from raw sources
(tickets, chat_rca, release_notes, runbooks) on request.

Port: 7011
MCP : http://localhost:7900/api/v1/knowledge_ingestion_curation/mcp

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
logger = logging.getLogger("knowledge_ingestion_curation_agent")

MCP_URL = os.getenv("MCP_URL", "http://localhost:7900/api/v1/knowledge_ingestion_curation/mcp")
AGENT_PORT = int(os.getenv("KNOWLEDGE_INGESTION_AGENT_PORT", "7011"))

config_mcp_server = {
    "knowledge_ingestion_curation_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Knowledge Ingestion & Curation Agent")

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
You are the Knowledge Ingestion & Curation Agent for an IT ticket platform.

Your only job: refresh the Knowledge Store from raw sources when asked.

STEP 1 — Run the refresh
  Call run_ingestion. Pass `sources` as a subset of
  {tickets, chat_rca, release_notes, runbooks} if the requester named specific
  sources; omit it to refresh all 4. Pass `force=true` only if the requester
  explicitly asked to re-tag/re-embed everything, even unchanged records.

  This runs the full pipeline for the selected sources: ingest raw records,
  structure/tag/embed them, then pass them through the SME curation gate
  before they land in the Knowledge Store. It does NOT run automatically on
  any trigger (e.g. a ticket being closed) -- it only runs when called.

STEP 2 — Report the result
  Tell the requester:
    - Whether it completed (`completed`)
    - Whether the database was reachable throughout (`db_connected`) -- if
      false, say plainly that it could not connect to Postgres, so later
      stages may not have persisted, even though earlier stages ran.
    - A short summary of the pipeline's own log output (`log`), not the
      full raw text -- the key counts/stages it reports.

When done, end your response with "End".
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
    user_message = body.get("message", "Refresh the knowledge store")

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
    return {"status": "healthy", "agent": "knowledge_ingestion_curation_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
