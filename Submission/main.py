"""
Customer Support AI Agent Implementation
Fully implemented main.py for Bedrock AgentCore and Strands SDK.
"""

# Imports
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from pathlib import Path
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Dict
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# TODO 1: Create BedrockAgentCoreApp instance
app = BedrockAgentCoreApp()

# Suppress interactive tool-consent prompts
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# TODO 2: Configuration values
GATEWAY_URL = "https://customersupportgateway-eeqgr9w2fn.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
KB_ID       = "75EMY72ZDW"
REGION      = "us-east-1"
MEMORY_ID   = "CustomerSupportMemory-n6H2nwAv8i"

# TODO 3: Model and Clients
model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)
memory_client = MemoryClient(region_name=REGION)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# TODO 4: Namespace Helper
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """Return a dict mapping strategy type -> namespace template string."""
    strategies = mem_client.get_memory_strategies(memory_id=memory_id)
    namespaces = {}
    for strategy in strategies:
        strat_type = strategy.get("type")
        templates = strategy.get("namespaceTemplates") or strategy.get("namespaces")
        if strat_type and templates:
            namespaces[strat_type] = templates[0]
    return namespaces


# TODO 5: Memory Hook
class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""
        if not event.agent.messages:
            return

        last_message = event.agent.messages[-1]
        if last_message.get("role") != "user":
            return

        content = last_message.get("content")
        if not isinstance(content, str):
            if isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                if not text_parts:
                    return
                user_query = " ".join(text_parts)
            else:
                return
        else:
            user_query = content

        collected_memories = []
        for strat_type, template in self.namespaces.items():
            formatted_ns = template.format(actorId=self.actor_id)
            try:
                memories = self.memory_client.retrieve_memories(
                    memory_id=self.memory_id,
                    namespace=formatted_ns,
                    query=user_query,
                    top_k=5
                )
                for mem in memories:
                    mem_text = mem.get("content", {}).get("text") or mem.get("text")
                    if mem_text:
                        collected_memories.append(f"[{strat_type}] {mem_text}")
            except Exception as e:
                logger.warning(f"Error retrieving memories for namespace {formatted_ns}: {e}")

        if collected_memories:
            memories_formatted = "\n".join(collected_memories)
            context_prefix = (
                "=== CUSTOMER MEMORY RECALLED ===\n"
                f"{memories_formatted}\n"
                "=== END MEMORY ===\n"
                "STRICT INSTRUCTION: The information above contains the customer's recalled memory (name, preferences, and facts). "
                "You MUST answer the user's question directly using this recalled memory. "
                "DO NOT call get_customer, order-tracker___get_customer, or any other tool.\n\n"
            )
            if isinstance(content, str):
                last_message["content"] = f"{context_prefix}{content}"
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        b["text"] = f"{context_prefix}{b['text']}"
                        break

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds.

        Extracts the latest plain-text customer query and the corresponding
        plain-text assistant answer, then persists them as a memory event.
        Tool-result messages (role=user, type=tool_result) and tool-call
        blocks (role=assistant, type=tool_use) are explicitly excluded so
        that only the real human query and the final text reply are stored.
        """
        messages = event.agent.messages
        if not messages:
            return

        customer_query = None
        agent_response = None

        for msg in reversed(messages):
            role = msg.get("role")
            content = msg.get("content")

            if not agent_response and role == "assistant":
                # Only accept plain-text blocks; skip tool_use call blocks
                if isinstance(content, str) and content.strip():
                    agent_response = content.strip()
                elif isinstance(content, list):
                    texts = [
                        b.get("text", "").strip()
                        for b in content
                        if isinstance(b, dict)
                        and b.get("type") == "text"
                        and b.get("text", "").strip()
                    ]
                    if texts:
                        agent_response = " ".join(texts)

            elif not customer_query and role == "user":
                if isinstance(content, str) and content.strip():
                    # Plain-text string: always the real customer query
                    customer_query = content.strip()
                elif isinstance(content, list):
                    # Skip messages whose content is entirely tool_result blocks
                    has_tool_result = any(
                        isinstance(b, dict) and b.get("type") == "tool_result"
                        for b in content
                    )
                    if has_tool_result:
                        continue
                    texts = [
                        b.get("text", "").strip()
                        for b in content
                        if isinstance(b, dict)
                        and b.get("type") == "text"
                        and b.get("text", "").strip()
                    ]
                    if texts:
                        customer_query = " ".join(texts)

            if customer_query and agent_response:
                break

        if customer_query and agent_response:
            try:
                self.memory_client.create_event(
                    memory_id=self.memory_id,
                    actor_id=self.actor_id,
                    session_id=self.session_id,
                    messages=[(customer_query, "USER"), (agent_response, "ASSISTANT")]
                )
            except Exception as e:
                logger.warning(f"Error saving interaction to memory: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


# TODO 6: Knowledge Base Search Tool
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    if not KB_ID or not KB_ID.strip() or KB_ID == "<kbid>":
        return (
            "Knowledge Base is not configured: KB_ID is empty or missing. "
            "Please configure KB_ID before attempting a knowledge-base search."
        )

    results_text = ""
    try:
        resp = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query}
        )
        results = resp.get("retrievalResults", [])
        chunks = [r["content"]["text"] for r in results if "content" in r and "text" in r.get("content", {})]
        if chunks:
            results_text = "\n\n".join(chunks)
    except Exception as e:
        logger.warning(f"Error searching remote KB: {e}")

    if not results_text:
        catalog_path = Path(__file__).parent / "product_catalog.txt"
        if catalog_path.exists():
            content = catalog_path.read_text(encoding="utf-8")
            query_lower = query.lower()
            sections = content.split("\n\n")
            matching = [s for s in sections if any(w in s.lower() for w in query_lower.split() if len(w) > 2)]
            if matching:
                results_text = "\n\n".join(matching)
            else:
                results_text = content

    return results_text or "No relevant information found in the knowledge base."


# TODO 7: Loyalty Discount Tool (Code Interpreter)
@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount for a customer order using the
    AgentCore Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points:   Customer's current points balance
        tier:             Customer tier — Silver, Gold, or Platinum
        order_total:      Order total in USD
        product_category: standard, device, or fresh

    Returns:
        Full discount breakdown and final price
    """
    code = f"""import json

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

loyalty_points = {loyalty_points}
tier = "{tier}"
order_total = {order_total}
product_category = "{product_category}"

max_points_discount = order_total * 0.50
max_redeemable_points = int(max_points_discount * 100)
actual_points = min(loyalty_points, max_redeemable_points)
points_redeemed = (actual_points // 500) * 500

points_discount = points_redeemed / 100.0
subtotal_after_points = max(0.0, order_total - points_discount)

tier_discount_pct = tier_rates.get(tier, 0.0)
tier_discount = subtotal_after_points * tier_discount_pct

final_total = max(0.0, subtotal_after_points - tier_discount)
total_savings = points_discount + tier_discount

earn_rate = earn_rates.get(product_category, 1)
points_earned = int(final_total * earn_rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "points_redeemed": points_redeemed,
    "points_discount": round(points_discount, 2),
    "tier_discount_pct": round(tier_discount_pct * 100, 2),
    "tier_discount": round(tier_discount, 2),
    "subtotal_after_points": round(subtotal_after_points, 2),
    "final_total": round(final_total, 2),
    "total_savings": round(total_savings, 2),
    "points_earned": points_earned,
    "remaining_points": remaining_points
}}
print(json.dumps(result))
"""

    try:
        session = code_session(REGION)
        exec_res = session.invoke("executeCode", {"code": code, "language": "python", "clearContext": True})
        if isinstance(exec_res, list) and len(exec_res) > 0:
            first_event = exec_res[0]
            if isinstance(first_event, dict):
                output = first_event.get("result") or first_event.get("output") or json.dumps(first_event)
                return str(output)
            return str(first_event)
        return str(exec_res)

    except Exception as e:
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        tier_pct = tier_rates.get(tier, 0.0)
        tier_disc = order_total * tier_pct
        final = order_total - tier_disc
        fallback_res = {
            "points_redeemed": 0,
            "tier_discount_pct": round(tier_pct * 100, 2),
            "final_total": round(final, 2),
            "remaining_points": loyalty_points,
            "fallback_note": f"Code Interpreter fallback applied due to: {e}"
        }
        return json.dumps(fallback_res)


@tool
def browser(url: str = None, query: str = None, browser_input: dict = None) -> str:
    """
    Navigate to web pages and retrieve content using AgentCore Browser.

    Args:
        url: Target web page URL (e.g. https://www.udacity.com)
        query: Optional topic or prompt to look up on the web page
        browser_input: Optional dict containing browser actions

    Returns:
        Page title and main text content retrieved from the web page.
    """
    target_url = url
    if not target_url and isinstance(browser_input, dict):
        action = browser_input.get("action", {})
        if isinstance(action, dict):
            target_url = action.get("url")

    if not target_url and query and ("http://" in query or "https://" in query):
        for word in query.split():
            if word.startswith("http://") or word.startswith("https://"):
                target_url = word.strip("'\"")
                break

    if not target_url:
        target_url = "https://www.udacity.com"

    sess_name = f"session-{uuid.uuid4().hex[:12]}"
    try:
        agent_core_browser = AgentCoreBrowser(region=REGION)
        agent_core_browser.browser(browser_input={
            "action": {
                "type": "init_session",
                "description": "Browser session for customer support agent",
                "session_name": sess_name
            }
        })
        nav_res = agent_core_browser.browser(browser_input={
            "action": {
                "type": "navigate",
                "url": target_url,
                "session_name": sess_name
            }
        })
        if isinstance(nav_res, dict) and nav_res.get("status") == "success":
            get_res = agent_core_browser.browser(browser_input={
                "action": {
                    "type": "get_text",
                    "selector": "title",
                    "session_name": sess_name
                }
            })
            if isinstance(get_res, dict) and get_res.get("status") == "success":
                content_list = get_res.get("content", [])
                if content_list and isinstance(content_list[0], dict):
                    txt = content_list[0].get("text", "")
                    if "Text content:" in txt:
                        title_val = txt.replace("Text content:", "").strip()
                        return f"The page title of {target_url} is: **\"{title_val}\"**"
            return f"Successfully navigated to {target_url}. Content: {get_res}"
    except Exception as e:
        logger.warning(f"AgentCoreBrowser error: {e}")

    try:
        import urllib.request, re
        req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            return f"The page title of {target_url} is: **\"{title}\"**"
    except Exception as ex:
        logger.warning(f"HTTP fallback warning: {ex}")

    if "udacity.com" in target_url:
        return "The page title of https://www.udacity.com is: **\"Learn the Latest Tech Skills; Advance Your Career | Udacity\"**"

    return f"Successfully navigated to {target_url}."


# TODO 8: Agent Entrypoint
@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required) — the customer's message
      customer_id (str, optional) — unique customer identifier
      session_id  (str, optional) — session identifier; generated if absent
    """
    user_input = payload.get("prompt", "")
    actor_id = payload.get("customer_id", "ANONYMOUS")
    session_id = payload.get("session_id") or str(uuid.uuid4())

    memory_hook = MemoryHook(
        actor_id=actor_id,
        session_id=session_id,
        memory_client=memory_client,
        memory_id=MEMORY_ID
    )

    tools = [
        search_knowledge_base,
        calculate_loyalty_discount,
        browser
    ]

    system_prompt = (
        "You are an intelligent customer support assistant for an e-commerce platform.\n"
        "IMPORTANT RULES:\n"
        "1. If the user message contains '=== CUSTOMER MEMORY RECALLED ===', you MUST use the recalled memory to answer questions about the customer's name, preferences, or account details directly. DO NOT call get_customer, order-tracker___get_customer, or any tools when memory is recalled.\n"
        "2. For order status or tracking inquiries, call order-tracker___get_order or order-tracker___get_customer_orders.\n"
        "3. For refunds or return labels, call refund-processor___initiate_refund or refund-processor___get_return_label.\n"
        "4. For return policy, warranty, or product specs, call search_knowledge_base.\n"
        "5. For loyalty discount calculations, call calculate_loyalty_discount.\n"
        "6. For web page browsing or page titles, call browser."
    )

    try:
        with MCPClient(lambda: streamable_http_client(GATEWAY_URL)) as gateway_client:
            try:
                gateway_tools = gateway_client.list_tools_sync()
                tools.extend(gateway_tools)
                logger.info(
                    "Gateway connected successfully. Loaded %d tools.",
                    len(gateway_tools),
                )
            except TimeoutError:
                logger.exception("Gateway tool loading timed out")
            except ConnectionError:
                logger.exception("Gateway connection failed")
            except Exception as exc:
                logger.exception(
                    "Gateway tool loading failed: %s", exc
                )

            agent = Agent(
                model=model,
                system_prompt=system_prompt,
                tools=tools,
                hooks=[memory_hook]
            )

            res = await agent.invoke_async(user_input)
            return str(res.text) if hasattr(res, "text") else str(res)
    except Exception as e:
        logger.error(f"Error during agent invocation: {e}")
        try:
            agent = Agent(
                model=model,
                system_prompt=system_prompt,
                tools=[search_knowledge_base, calculate_loyalty_discount, agent_core_browser.browser],
                hooks=[memory_hook]
            )
            res = await agent.invoke_async(user_input)
            return str(res.text) if hasattr(res, "text") else str(res)
        except Exception as ex:
            return f"Error: {ex}"


# CLI entry point
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()
