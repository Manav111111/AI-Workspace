import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider

logger = logging.getLogger("app.services.evaluation.judge")

REFUSAL_SIGNATURES = [
    "not currently available in the company knowledge base",
    "not available in the company knowledge base",
    "i am sorry, but i don't know",
    "i do not have information",
    "i don't have information",
    "unable to find",
    "no information",
    "cannot find details",
]


class GenerationJudge:
    """Evaluates generation quality:
    - Faithfulness (LLM-as-a-judge checking claim grounding)
    - Answer Relevance (evaluating response against ground-truth reference)
    - Refusal Accuracy (verifying that out-of-scope queries trigger clean refusal)
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    @staticmethod
    def evaluate_refusal(generated_answer: str) -> bool:
        """Determines if the generated response correctly executes zero-retrieval refusal
        without hallucinating factual assertions.
        """
        if not generated_answer or not generated_answer.strip():
            return True

        text_lower = generated_answer.lower()
        return any(sig in text_lower for sig in REFUSAL_SIGNATURES)

    async def evaluate_faithfulness(
        self,
        context_chunks: List[str],
        generated_answer: str,
    ) -> Tuple[float, str]:
        """Evaluates whether all claims in generated_answer are grounded in context_chunks.
        Returns: (faithfulness_score: float, reasoning: str)
        """
        if not generated_answer or not generated_answer.strip():
            return 1.0, "Empty response has no ungrounded claims."

        if not context_chunks:
            # If no context was provided, any affirmative factual claim is ungrounded
            if self.evaluate_refusal(generated_answer):
                return 1.0, "Properly refused when no context was present."
            return 0.0, "Generated answer without any supporting context chunks."

        combined_context = "\n---\n".join(context_chunks)

        judge_prompt = f"""You are a strict, objective AI evaluation judge assessing RAG faithfulness.
Your task is to determine whether EVERY factual claim in the AI response is directly supported by the retrieved context.

=== RETRIEVED CONTEXT ===
{combined_context}

=== AI GENERATED ANSWER ===
{generated_answer}

Analyze the AI generated answer sentence by sentence.
Break it into atomic factual statements and verify each against the context.
Reply ONLY with a valid JSON object matching this schema:
{{
  "claims": [
    {{"claim": "statement text", "supported": true, "reason": "found in paragraph X"}},
    {{"claim": "statement text", "supported": false, "reason": "not mentioned in context"}}
  ],
  "faithfulness_score": 1.0,
  "summary_reasoning": "brief summary explanation"
}}
The faithfulness_score must be a float between 0.0 and 1.0 representing (supported_claims / total_claims). If there are no factual claims, output 1.0.
JSON:"""

        try:
            resp = await self.llm.generate(
                messages=[
                    {"role": "system", "content": "You are a precise evaluation judge. Output only JSON."},
                    {"role": "user", "content": judge_prompt},
                ],
                temperature=0.0,
                max_tokens=600,
            )

            raw_text = resp.content.strip()
            # Clean possible markdown fence
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text)

            data = json.loads(raw_text.strip())
            score = float(data.get("faithfulness_score", 1.0))
            reasoning = data.get("summary_reasoning", "Evaluated by LLM judge.")
            return min(1.0, max(0.0, round(score, 4))), reasoning

        except Exception as e:
            logger.warning(f"LLM faithfulness judge failed, falling back to lexical grounding heuristic: {e}")
            return self._heuristic_grounding_score(context_chunks, generated_answer)

    @staticmethod
    def _heuristic_grounding_score(
        context_chunks: List[str],
        generated_answer: str,
    ) -> Tuple[float, str]:
        """Deterministic lexical token grounding heuristic when LLM judge is unavailable."""
        if not context_chunks:
            return 0.5, "Heuristic: No context chunks available."

        context_tokens = set(re.findall(r"\w+", " ".join(context_chunks).lower()))
        answer_words = re.findall(r"\w+", generated_answer.lower())

        if not answer_words:
            return 1.0, "Heuristic: Empty answer."

        # Filter out common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "to", "in", "for", "of",
            "and", "or", "on", "with", "at", "by", "from", "as", "be", "that", "this",
            "it", "not", "have", "has", "had", "will", "our", "your", "we", "you"
        }
        content_words = [w for w in answer_words if w not in stop_words and len(w) > 2]
        if not content_words:
            return 1.0, "Heuristic: Answer contains only common words."

        matched = sum(1 for w in content_words if w in context_tokens)
        score = round(matched / len(content_words), 4)
        return score, f"Heuristic grounding: {matched}/{len(content_words)} content tokens grounded in context."

    @staticmethod
    def evaluate_answer_relevance(
        reference_answer: Optional[str],
        generated_answer: str,
    ) -> Tuple[float, str]:
        """Calculates token overlap and key entity recall between generated and reference answer."""
        if not reference_answer or not reference_answer.strip():
            return 1.0, "No reference answer provided for relevance scoring."
        if not generated_answer or not generated_answer.strip():
            return 0.0, "Generated answer is empty."

        ref_tokens = set(re.findall(r"\w+", reference_answer.lower()))
        gen_tokens = set(re.findall(r"\w+", generated_answer.lower()))

        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "to", "in", "for", "of",
            "and", "or", "on", "with", "at", "by", "from", "as", "be", "that", "this",
            "it", "not", "have", "has", "had", "will", "our", "your", "we", "you"
        }
        sig_ref = [t for t in ref_tokens if t not in stop_words and len(t) > 2]
        if not sig_ref:
            return 1.0, "Reference answer contains only stopwords."

        hits = sum(1 for t in sig_ref if t in gen_tokens)
        score = min(1.0, round(hits / len(sig_ref), 4))
        return score, f"Entity recall vs reference: {hits}/{len(sig_ref)} tokens matched."
