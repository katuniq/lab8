# Comparison: Baseline vs. Variant

**Date:** 2026-04-13  
**Evaluation Period:** Sprint 3 & 4  
**Total Test Questions:** 10

---

## Executive Summary

Tested two configurations:
1. **Baseline (Dense Only):** Pure embedding-based retrieval
2. **Variant (Hybrid):** Dense + BM25 keyword search with RRF fusion

### Overall Results

| Configuration | Faithfulness | Relevance | Completeness | Context Recall | **Overall Average** |
|---|---|---|---|---|---|
| **Baseline Dense** | 2.60/5 | 4.40/5 | 5.00/5 | 4.80/5 | **4.20/5** |
| **Variant Hybrid** | 2.50/5 | 4.00/5 | 5.00/5 | 4.80/5 | **4.08/5** |
| **Δ (Delta)** | -0.10 | -0.40 | 0.00 | 0.00 | **-0.12** |

---

## Detailed Metric Breakdown

### Faithfulness (Grounding in Retrieved Context)
- **Baseline:** 2.60/5 — Answers often contain external model knowledge beyond retrieved context
- **Variant:** 2.50/5 — Slightly lower, BM25 didn't improve grounding
- **Analysis:** Both struggle with faithfulness; hybrid's keyword matching didn't help prevent hallucinations

### Relevance (Query Answering)
- **Baseline:** 4.40/5 — Strong query-answer alignment
- **Variant:** 4.00/5 — Slightly reduced (-0.40)
- **Analysis:** Hybrid relevance dropped because BM25 added some off-topic keyword hits

### Completeness (All Query Aspects Covered)
- **Baseline:** 5.00/5 — Complete coverage consistently
- **Variant:** 5.00/5 — Maintained completeness
- **Analysis:** Both perform equally well; no difference in answer thoroughness

### Context Recall (Retrieved All Necessary Sources)
- **Baseline:** 4.80/5 — Retrieved correct documents
- **Variant:** 4.80/5 — Same as baseline
- **Analysis:** Hybrid didn't improve document recall; queries were already semantic-friendly

---

## Hybrid Variant Deep-Dive

### Configuration
```json
{
  "retrieval_mode": "hybrid",
  "dense_weight": 0.6,
  "sparse_weight": 0.4,
  "rrf_constant": 60,
  "top_k_search": 10,
  "top_k_select": 3
}
```

### Why Hybrid Performed Worse
1. **Query Type:** 80% of test queries are naturally semantic (e.g., "SLA xử lý ticket P1")
   - Dense retrieval already captures these well
   - BM25 added noise by matching unrelated keywords

2. **Corpus Characteristics:**
   - No heavy acronyms/codes requiring keyword matching (except ERR-403)
   - Documents use consistent terminology
   - Semantic distance is reliable for this corpus

3. **RRF Weighting Issue:**
   - 0.6/0.4 split may not be optimal for this corpus
   - BM25 scores sometimes dominated for wrong reasons

### Questions Where Hybrid Performed Different

| # | Query | Baseline | Hybrid | Winner | Why |
|---|-------|----------|--------|--------|-----|
| 1 | SLA P1 duration | R:4, F:2 | R:3, F:2 | Baseline | Dense was more focused |
| 6 | Escalation explanation | R:5, F:3 | R:3, F:2 | Baseline | Hybrid got more results than needed |
| 8 | Remote work policy | R:4, F:3 | R:3, F:3 | Baseline | More precision from dense |
| 9 | ERR-403-AUTH error | R:5, CR:3 | R:5, CR:3 | TIE | Both abstained correctly |

---

## Conclusion & Recommendations

### Winner: **BASELINE (Dense Only)** ✅

**Verdict:** Baseline performs better on this corpus by +0.12 points overall.

**Reasoning:**
1. **Relevance:** Dense consistently more focused (-0.40 delta is significant)
2. **Consistency:** No category improved; Context Recall and Completeness unchanged
3. **Efficiency:** Dense is faster than hybrid + BM25
4. **Trade-off Analysis:** No upside from complexity

### Why NOT Use Hybrid for This Project

This corpus is **unsuitable for hybrid retrieval** because:
- ✅ Terminology is consistent (no alias/old names to handle)
- ✅ Most queries are already semantic (not keyword-heavy)
- ✅ Small corpus (29 chunks) → dense already powerful enough
- ❌ Hybrid adds noise without improving performance

### When Hybrid WOULD Help

Hybrid would be better if:
- Corpus had mixed terminology (e.g., "SLA" vs. "Service Level Agreement")
- Many error codes or acronyms (e.g., ticket for ERR-403-AUTH)
- Different document versions with old/new names

---

## Recommendations for Sprint 4+

### Keep Baseline as Production
- Stick with dense-only retrieval
- Continue with current LLM settings

### Consider Alternative Improvements
Instead of hybrid, try:
1. **Prompt Tuning** — Add more grounding instructions
2. **Query Expansion** — Handle "Approval Matrix" → "Access Control SOP" alias
3. **Better Chunking** — Metadata-aware chunking for better recall
4. **Few-shot Examples** — In-context learning for grounding

### If Variants MUST Be Tested
- Test Query Expansion for question #7 (Approval Matrix)
- Test Reranking for high-volume retrieval (> 10K chunks)

---

## Appendix: Raw Scores

### Baseline Scores by Question
```
Q1: F=2, R=4, Co=5, CR=5
Q2: F=3, R=5, Co=5, CR=5
Q3: F=2, R=4, Co=5, CR=5
Q4: F=3, R=5, Co=5, CR=5
Q5: F=3, R=5, Co=5, CR=5
Q6: F=3, R=5, Co=5, CR=5
Q7: F=1, R=2, Co=5, CR=5
Q8: F=3, R=4, Co=5, CR=5
Q9: F=3, R=5, Co=5, CR=3
Q10: F=3, R=5, Co=5,CR=5
```

### Hybrid Scores by Question
```
Q1: F=2, R=3, Co=5, CR=5
Q2: F=3, R=5, Co=5, CR=5
Q3: F=2, R=4, Co=5, CR=5
Q4: F=3, R=5, Co=5, CR=5
Q5: F=3, R=5, Co=5, CR=5
Q6: F=2, R=3, Co=5, CR=5
Q7: F=1, R=2, Co=5, CR=5
Q8: F=3, R=3, Co=5, CR=5
Q9: F=3, R=5, Co=5, CR=3
Q10: F=3, R=5, Co=5, CR=5
```
