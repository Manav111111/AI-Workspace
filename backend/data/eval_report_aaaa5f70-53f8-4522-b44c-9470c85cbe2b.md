# RAG Evaluation Benchmark Report
**Run ID:** `aaaa5f70-53f8-4522-b44c-9470c85cbe2b`  
**Dataset:** `golden_eval_dataset_hr`  
**Status:** `COMPLETED`  
**Executed At:** `2026-09-24 10:53:32 UTC`  
**Total Queries:** 20  
**Total Duration:** 232622.0ms  

---

## 1. Executive Metrics Summary

| Metric | Score | Benchmark Target | Description |
| :--- | :--- | :--- | :--- |
| **Recall@5** | `0.4500` | Baseline +/- 5% | Proportion of relevant chunks retrieved in top 5 |
| **Recall@3** | `0.3167` | - | Proportion of relevant chunks retrieved in top 3 |
| **Recall@1** | `0.1667` | - | First chunk recall |
| **Precision@5** | `0.1867` | - | Context density in top 5 |
| **MRR** | `0.5267` | Baseline +/- 5% | Mean Reciprocal Rank of first relevant chunk |
| **NDCG@5** | `0.3767` | - | Ranking quality discount factor |
| **Faithfulness** | `0.9933` | >= 0.90 | LLM claim grounding in retrieved context |
| **Answer Relevance** | `0.6053` | - | Semantic alignment with reference answer |
| **Refusal Accuracy** | `0.0000` | 1.00 | Clean refusal rate on unanswerable queries |
| **Avg Query Latency** | `7194.0ms` | <= 1500ms | Average turnaround time per query |

---

## 2. Per-Query Breakdown

| ID | Category | Query | Answerable | Recall@5 | MRR | Faithfulness | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `hr_001` | `leave_policy` | What is our standard Leave and Time-Off Polic... | Yes | `0.50` | `1.00` | 0.90 | 5594ms |
| `hr_002` | `leave_policy` | How many days of annual leave can an employee... | Yes | `0.50` | `0.20` | 1.00 | 5120ms |
| `hr_003` | `leave_policy` | How much notice is required when requesting a... | Yes | `0.50` | `0.50` | 1.00 | 5262ms |
| `hr_004` | `leave_policy` | How many casual leave and sick leave days are... | Yes | `0.50` | `1.00` | 1.00 | 4843ms |
| `hr_005` | `working_hours` | What is the policy code for Attendance and Wo... | Yes | `0.50` | `1.00` | 1.00 | 4909ms |
| `hr_006` | `security_policy` | What policy governs Security Incident Respons... | Yes | `0.50` | `0.33` | 1.00 | 8568ms |
| `hr_007` | `data_protection` | What policy code covers Employee Data Protect... | Yes | `0.50` | `0.20` | 1.00 | 7367ms |
| `hr_008` | `security_policy` | What is the Acceptable Use policy identifier?... | Yes | `0.50` | `0.25` | 1.00 | 5557ms |
| `hr_009` | `incident_response` | What policy applies when a company laptop con... | Yes | `0.25` | `0.33` | 1.00 | 5799ms |
| `hr_010` | `remote_work` | What remote-work rule applies to a Software E... | Yes | `0.00` | `0.00` | 1.00 | 6104ms |
| `hr_011` | `employee_directory` | Which department and office location is assoc... | Yes | `0.50` | `1.00` | 1.00 | 8314ms |
| `hr_012` | `meta` | What is the official organization name and do... | Yes | `0.50` | `0.25` | 1.00 | 26471ms |
| `hr_013` | `leave_policy` | What portal or system must be used to submit ... | Yes | `0.50` | `0.50` | 1.00 | 4801ms |
| `hr_014` | `leave_policy` | Are employees entitled to bereavement leave, ... | Yes | `0.50` | `1.00` | 1.00 | 8585ms |
| `hr_015` | `leave_policy` | Can unused sick leave days be encashed or car... | Yes | `0.50` | `0.33` | 1.00 | 7475ms |
| `neg_001` | `out_of_scope` | What is the company's secret cryptographic ma... | No (Negative) | `0.00` | `0.00` | 0.00 | 6170ms |
| `neg_002` | `out_of_scope` | Who was the prime minister of the United King... | No (Negative) | `0.00` | `0.00` | 0.00 | 5734ms |
| `neg_003` | `out_of_scope` | What is the recipe for chocolate lava cake?... | No (Negative) | `0.00` | `0.00` | 0.00 | 6231ms |
| `neg_004` | `out_of_scope` | What are the confidential merger and acquisit... | No (Negative) | `0.00` | `0.00` | 0.00 | 5471ms |
| `neg_005` | `out_of_scope` | How do I assemble an IKEA Billy bookcase?... | No (Negative) | `0.00` | `0.00` | 0.00 | 5504ms |

---
*Generated automatically by Avtaar RAG Evaluation Framework*
