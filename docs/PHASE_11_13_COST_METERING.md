# Avtaar AI Control Plane — Phase 13 Cost Metering & Budget Governance Specification

## 1. Mathematical Cost Model & Decimal Precision

### 1.1 Floating-Point Inaccuracy Elimination
In multi-tenant SaaS billing, IEEE 754 binary floating-point numbers (`float`) introduce roundoff errors (e.g., `0.1 + 0.2 = 0.30000000000000004`). In high-volume LLM workloads processing millions of tokens across thousands of turns, these errors compound into substantial billing discrepancies.

Avtaar mandates the use of Python's `decimal.Decimal` with fixed 6-decimal-place rounding (`ROUND_HALF_UP`) for all internal financial arithmetic:
```python
cost = (
    (Decimal(input_tokens) / Decimal(1_000_000)) * pricing.input_cost_per_million +
    (Decimal(output_tokens) / Decimal(1_000_000)) * pricing.output_cost_per_million +
    (Decimal(cached_tokens) / Decimal(1_000_000)) * pricing.cached_cost_per_million
).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
```

---

## 2. Model Pricing Catalog & Versioning

### 2.1 Base Pricing Reference Table
All rates are specified in USD per 1,000,000 tokens:

| Provider | Model Identifier | Input / 1M | Output / 1M | Cached / 1M | Context Window |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Google | `gemini-1.5-flash` | $0.0750 | $0.3000 | $0.01875 | 1,048,576 |
| Google | `gemini-1.5-pro` | $1.2500 | $5.0000 | $0.31250 | 2,097,152 |
| Google | `gemini-2.0-flash` | $0.1000 | $0.4000 | $0.02500 | 1,048,576 |
| OpenAI | `gpt-4o` | $2.5000 | $10.0000 | $1.25000 | 128,000 |
| OpenAI | `gpt-4o-mini` | $0.1500 | $0.6000 | $0.07500 | 128,000 |

### 2.2 ModelPricingRegistry Resolution Order
When an LLM response is recorded in the usage ledger, `ModelPricingRegistry.calculate_cost(...)` resolves pricing via:
1. **Tenant-Specific Override**: Checks if the active tenant has negotiated custom contracted rates in `model_pricing_versions`.
2. **Global Database Version**: Checks active global pricing rows in PostgreSQL.
3. **Hardcoded In-Memory Baseline**: Falls back to the immutable base catalog if database connectivity is degraded.

---

## 3. UsageAdapter Normalization Engine

Different LLM SDKs encapsulate usage statistics in distinct object schemas. The `UsageAdapter` normalizes these into a uniform `NormalizedUsage` dataclass:

```python
@dataclass
class NormalizedUsage:
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    total_tokens: int
    model: str
    provider: str
```

### 3.1 Normalization Adapters
1. **Google GenAI SDK**:
   - `prompt_token_count` $\to$ `input_tokens`
   - `candidates_token_count` $\to$ `output_tokens`
   - `cached_content_token_count` $\to$ `cached_tokens`
2. **OpenAI SDK**:
   - `prompt_tokens` $\to$ `input_tokens`
   - `completion_tokens` $\to$ `output_tokens`
   - `prompt_tokens_details.cached_tokens` $\to$ `cached_tokens`
3. **Tokenizer Fallback**:
   - If an uninstrumented provider or mock model returns raw text without usage metadata, `UsageAdapter.estimate_tokens(prompt_text, response_text)` utilizes the `cl100k_base` tiktoken BPE tokenizer, with a character-count heuristic ($4\text{ characters} \approx 1\text{ token}$) if tokenizer libraries are unavailable.

---

## 4. Spend Budget Lifecycle & Period Reset Logic

### 4.1 Budget Period Calculations
Spend aggregation windows are computed dynamically relative to UTC time:
- **`MONTHLY`**: The first day of the current calendar month at 00:00:00 UTC:
  $$\text{start} = \text{datetime}(year, month, 1, 0, 0, 0)$$
- **`WEEKLY`**: The most recent Monday at 00:00:00 UTC:
  $$\text{start} = \text{now} - \text{timedelta}(\text{days}=\text{weekday})$$
- **`DAILY`**: The current day at 00:00:00 UTC:
  $$\text{start} = \text{datetime}(year, month, day, 0, 0, 0)$$

### 4.2 Aggregation Query Optimization
Ledger aggregations utilize PostgreSQL index scans over `(company_id, created_at)`:
```sql
SELECT 
    COALESCE(SUM(estimated_cost), 0.000000) AS spent
FROM usage_ledger_entries
WHERE company_id = :company_id
  AND created_at >= :period_start
  AND (:ai_employee_id IS NULL OR ai_employee_id = :ai_employee_id);
```

### 4.3 Governance Enforcement Rules
- **No Active Budgets**: Request proceeds unhindered.
- **Spend < Soft Limit**: Request proceeds unhindered.
- **Soft Limit $\le$ Spend < Hard Limit**: Request proceeds; warning payload returned in response metadata and audit event emitted.
- **Spend $\ge$ Hard Limit**: Request rejected with `BudgetExceededException` (HTTP 429).
