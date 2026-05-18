import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from app.agent.tools.floe_tools import (
    set_floe_wallet,
    check_credit_status,
    estimate_x402_cost,
    post_borrow_intent,
    repay_credit,
)
from app.agent.prompts import SYSTEM_PROMPT
import structlog

log = structlog.get_logger()

TOOLS = [check_credit_status, estimate_x402_cost, post_borrow_intent, repay_credit]


def build_agent(wallet_provider=None):
    """
    Build the agent with optional wallet provider for on-chain operations.

    Args:
        wallet_provider: Wallet provider for on-chain Floe operations
                        (EvmWalletProvider, CdpWalletProvider, etc.)
    """
    if wallet_provider:
        set_floe_wallet(wallet_provider)
        log.info("agent_built_with_wallet_provider", provider_type=type(wallet_provider).__name__)
    else:
        log.warning("agent_built_without_wallet_provider")

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    return create_react_agent(llm, TOOLS)


async def run_task(task_description: str, wallet_provider=None) -> dict:
    """
    Execute a task using the Floe Budget Agent.

    Args:
        task_description: What the agent should do
        wallet_provider: Wallet provider for on-chain operations

    Returns:
        Result dict with success status and output
    """
    agent = build_agent(wallet_provider=wallet_provider)
    log.info("task_started", task=task_description)

    try:
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": task_description
                    }
                ]
            }
        )
        output = result["messages"][-1].content
        log.info("task_completed", output=output)
        return {"success": True, "output": output}
    except Exception as e:
        log.error("task_failed", error=str(e))
        return {"success": False, "error": str(e)}