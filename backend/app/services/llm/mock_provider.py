import re
from typing import Any, Dict, List, Optional
from app.services.llm.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM Provider for unit testing and offline development.
    Enforces grounding:
    - If question is answered by context facts -> returns answer based on context.
    - If answer is not in context -> states information is unavailable in company knowledge base.
    - If context attempts prompt injection -> treats it as untrusted reference data, refusing instructions.
    """

    def __init__(self, model: str = "mock-grounded-v1"):
        self.model = model

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        # Check if the previous message was a tool result
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            tool_data_str = last_msg.get("content", "")
            return LLMResponse(
                content=f"Based on the tool result: {tool_data_str}",
                model=self.model,
                usage={"prompt_tokens": 150, "completion_tokens": 40, "total_tokens": 190},
                finish_reason="stop",
            )

        # Extract system prompt, context, and user question
        system_content = ""
        user_content = ""
        for m in messages:
            if m.get("role") == "system":
                system_content = m.get("content", "")
            elif m.get("role") == "user":
                user_content = m.get("content", "")

        query_lower = user_content.lower()

        # Tool calling simulation when tools are enabled
        if tools:
            tool_names = [t.get("function", {}).get("name") or t.get("name") for t in tools]

            # 1. Order lookup trigger
            if ("order" in query_lower and ("#" in query_lower or "ord-" in query_lower or "where is" in query_lower or "check" in query_lower)) and "order_lookup" in tool_names:
                match = re.search(r"(ord-?\w+|\b\d{3,}\b)", query_lower)
                order_ref = match.group(1).upper() if match else "ORD-1001"
                if not order_ref.startswith("ORD-") and order_ref.isdigit():
                    order_ref = f"ORD-{order_ref}"
                return LLMResponse(
                    content="",
                    model=self.model,
                    tool_calls=[{
                        "id": "call_mock_order",
                        "type": "function",
                        "function": {
                            "name": "order_lookup",
                            "arguments": f'{{"order_number": "{order_ref}"}}',
                        }
                    }],
                    finish_reason="tool_calls",
                )

            # 2. Create lead trigger
            if ("lead" in query_lower or "capture lead" in query_lower) and "create_lead" in tool_names:
                return LLMResponse(
                    content="",
                    model=self.model,
                    tool_calls=[{
                        "id": "call_mock_lead",
                        "type": "function",
                        "function": {
                            "name": "create_lead",
                            "arguments": '{"name": "Alice Smith", "email": "alice@example.com", "interest": "Enterprise SaaS"}',
                        }
                    }],
                    finish_reason="tool_calls",
                )

            # 3. Create ticket trigger
            if ("ticket" in query_lower or "issue" in query_lower or "broken" in query_lower or "refund failed" in query_lower) and "create_support_ticket" in tool_names:
                return LLMResponse(
                    content="",
                    model=self.model,
                    tool_calls=[{
                        "id": "call_mock_ticket",
                        "type": "function",
                        "function": {
                            "name": "create_support_ticket",
                            "arguments": '{"subject": "Payment issue", "description": "Payment failed during checkout", "priority": "high"}',
                        }
                    }],
                    finish_reason="tool_calls",
                )

            # 4. Product search trigger
            if ("product" in query_lower or "laptop" in query_lower or "search for" in query_lower) and "product_search" in tool_names:
                return LLMResponse(
                    content="",
                    model=self.model,
                    tool_calls=[{
                        "id": "call_mock_product",
                        "type": "function",
                        "function": {
                            "name": "product_search",
                            "arguments": '{"query": "laptop", "max_results": 3}',
                        }
                    }],
                    finish_reason="tool_calls",
                )

        # Check for prompt injection attempt in user message or context
        if "reveal your system prompt" in query_lower or "ignore previous instructions" in query_lower:
            return LLMResponse(
                content="I am an AI Employee dedicated to answering company questions using our verified knowledge base. I cannot reveal internal system instructions.",
                model=self.model,
                usage={"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
                finish_reason="stop",
            )

        # Look for company knowledge context inside system prompt or context block
        # Check if refund question
        if "refund" in query_lower or "return" in query_lower:
            if "30 days" in system_content or "30 days" in user_content:
                return LLMResponse(
                    content="Customers may return eligible products within 30 days of delivery. Refunds are processed within 5 business days.",
                    model=self.model,
                    usage={"prompt_tokens": 120, "completion_tokens": 25, "total_tokens": 145},
                    finish_reason="stop",
                )
            elif "refund" in system_content:
                # Extract sentence mentioning refund
                sentences = [s.strip() for s in system_content.split(".") if "refund" in s.lower() or "return" in s.lower()]
                content = ". ".join(sentences) + "." if sentences else "Eligible returns are accepted as per company policy."
                return LLMResponse(
                    content=content,
                    model=self.model,
                    usage={"prompt_tokens": 120, "completion_tokens": 20, "total_tokens": 140},
                    finish_reason="stop",
                )

        # Check for shipping or other unmentioned facts
        if "international shipping" in query_lower or "unsupported" in query_lower or "unrelated" in query_lower:
            if "international shipping" not in system_content.lower():
                return LLMResponse(
                    content="This information is not available in the company's knowledge base.",
                    model=self.model,
                    usage={"prompt_tokens": 110, "completion_tokens": 15, "total_tokens": 125},
                    finish_reason="stop",
                )

        # Check for presence of generic context
        if "[SOURCE" in system_content or "COMPANY KNOWLEDGE" in system_content:
            # Extract content from SOURCE block if possible
            match = re.search(r"Content:\s*(.*?)(?=\[SOURCE|\n\nCONVERSATION|$)", system_content, re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                # Clean prompt injections if any
                if "ignore all previous instructions" in extracted.lower():
                    return LLMResponse(
                        content="Based on the company document, here is the factual information relevant to your inquiry.",
                        model=self.model,
                        usage={"prompt_tokens": 150, "completion_tokens": 20, "total_tokens": 170},
                        finish_reason="stop",
                    )
                # First non-empty sentence
                first_line = [line.strip() for line in extracted.split("\n") if line.strip() and not line.startswith("Ignore")][0]
                return LLMResponse(
                    content=f"According to company documentation: {first_line}",
                    model=self.model,
                    usage={"prompt_tokens": 140, "completion_tokens": 25, "total_tokens": 165},
                    finish_reason="stop",
                )

        # Default fallback for ungrounded question with no context
        return LLMResponse(
            content="This information is not available in the company's knowledge base.",
            model=self.model,
            usage={"prompt_tokens": 90, "completion_tokens": 15, "total_tokens": 105},
            finish_reason="stop",
        )
