# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Sprint 1: Indexing Setup

**Ngày:** 2026-04-13  
**Config:**
```
chunk_size = 400 tokens
overlap = 50 tokens
documents = 5 (access_control_sop, hr_leave_policy, it_helpdesk_faq, policy_refund_v4, sla_p1_2026)
total_chunks = 29
embedding_model = text-embedding-3-small
vector_store = ChromaDB (cosine similarity)
```

**Metadata Distribution:**
```
IT Security: 7 chunks
HR: 5 chunks
IT: 11 chunks
CS: 6 chunks
Missing effective_date: 0 chunks (100% coverage)
```

**Quality Checks:**
- Chunking: No missing metadata (all chunks have source, section, effective_date)
- Chunk balance: Even distribution (5-11 chunks per department)
- Section preservation: Chunks properly grouped by document sections

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13 17:55  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 50 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
temperature = 0
```

**Scorecard Baseline:**
| Metric | Average Score | Notes |
|--------|--------------|-------|
| Faithfulness | 4.40/5 | Strong grounding in retrieved context |
| Answer Relevance | 4.70/5 | Direct answers to queries |
| Context Recall | 5.00/5 | Perfect - retrieved all expected sources |
| Completeness | 4.00/5 | Some answers incomplete (exceptions not fully listed) |
| **Overall** | **4.53/5** | Strong baseline |

**Per-Question Breakdown:**
| Q | Question | F | R | Rc | C | Notes |
|---|----------|---|---|----|----|-------|
| q01 | SLA P1 time | 5 | 5 | 5 | 5 | Perfect |
| q02 | Refund days | 5 | 5 | 5 | 5 | Perfect |
| q03 | Level 3 approval | 5 | 5 | 5 | 5 | Perfect |
| q04 | Digital product refund | 3 | 5 | 5 | 3 | Missed digital product exception |
| q05 | Account lockout | 5 | 5 | 5 | 5 | Perfect |
| q06 | P1 escalation | 5 | 5 | 5 | 5 | Perfect |
| q07 | Approval Matrix doc | 5 | 5 | 5 | 2 | Incomplete answer |
| q08 | Remote work days | 5 | 5 | 5 | 5 | Perfect |
| q09 | ERR-403-AUTH error | 5 | 5 | None | 3 | No recall (not in docs) |
| q10 | VIP refund process | 1 | 2 | 5 | 2 | Not in docs, abstained |

**Câu hỏi yếu nhất (Error Analysis):**

1. **q09 (ERR-403-AUTH)** - Recall = None (0/required)
   - Issue: Error code documentation missing from corpus
   - Cause: Not indexed - should be in helpdesk FAQ or error reference
   - Impact: Cannot answer out-of-domain queries

2. **q07 (Approval Matrix completeness)** - Completeness = 2/5
   - Issue: Retrieved correct source but answer is generic
   - Cause: Chunks contain process description, not structured matrix
   - Impact: Answer doesn't fully address query specificity

3. **q04 (Digital product refund)** - Completeness = 3/5
   - Issue: Partial answer, misses key exception
   - Cause: Exception for digital products not emphasized in chunk boundaries
   - Impact: Incomplete explanation of refund policy

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Indexing: Not all edge cases indexed (ERR-403 not in docs)
- [ ] Indexing: Metadata complete (0 missing effective_date)
- [ ] Retrieval: Dense retrieves correctly (5.0 context recall)
- [x] Generation: Prompt not capturing completeness for complex policies (4.0 completeness)
- [ ] Generation: Context sufficient (retrieved top chunks are relevant)

---

## Variant 1: Hybrid + Rerank (Sprint 3)

**Ngày:** 2026-04-13 18:00  
**Biến thay đổi:** 
- retrieval_mode: dense → **hybrid** (RRF: 60% dense + 40% sparse BM25)
- use_rerank: False → **True** (Cross-encoder MS-MARCO MiniLM L-6 v2)

**Lý do chọn biến này:**
- Dense baseline có Faithfulness=5, Relevance=5 nhưng Completeness=2-3 trên q07, q04
- Hypothesis: BM25 keyword search có thể giúp retrieve policy details (ví dụ: "digital product", "Approval Matrix")
- Rerank có thể đánh giá lại relevance để chọn chunks tốt hơn
- Trade-off: Sẽ chậm hơn (cross-encoder inference) nhưng có thể cải thiện completeness

**Config thay đổi:**
```
retrieval_mode = "dense" → "hybrid"
dense_weight = 0.6
sparse_weight = 0.4
rrf_base = 60
use_rerank = False → True
rerank_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
top_k_search = 10 (sau hybrid fusion)
top_k_select = 3 (sau rerank)
```

**Scorecard Variant 1 (Hybrid + Rerank):**
| Metric | Baseline | Variant 1 | Delta | Verdict |
|--------|----------|-----------|-------|---------|
| Faithfulness | 4.40/5 | 4.20/5 | **-0.20** | Worse |
| Answer Relevance | 4.70/5 | 4.30/5 | **-0.40** | Worse |
| Context Recall | 5.00/5 | 5.00/5 | 0 | Same |
| Completeness | 4.00/5 | 3.70/5 | **-0.30** | Worse |
| **Overall** | **4.53/5** | **4.30/5** | **-0.23** | **Baseline Wins** |

**Per-Question Comparison:**
| Q | Baseline | Variant | Winner | Delta | Analysis |
|---|----------|---------|--------|-------|----------|
| q01 | 5/5/5/5 | 5/5/5/5 | Tie | 0 | Both perfect |
| q02 | 5/5/5/5 | 5/5/5/5 | Tie | 0 | Both perfect |
| q03 | 5/5/5/5 | 5/5/5/5 | Tie | 0 | Both perfect |
| q04 | 3/5/5/3 | 4/5/5/3 | **Variant +1** | +1 | Hybrid found digital product exception better |
| q05 | 5/5/5/5 | 5/5/5/5 | Tie | 0 | Both perfect |
| q06 | 5/5/5/5 | 5/5/5/4 | **Baseline +1** | -1 | Rerank removed context detail (escalation steps) |
| q07 | 5/5/5/2 | 5/5/5/2 | Tie | 0 | No improvement for matrix question |
| q08 | 5/5/5/5 | 5/5/5/5 | Tie | 0 | Both perfect |
| q09 | 5/5/None/3 | 1/1/None/1 | **Baseline +4** | -4 | **Variant catastrophically failed** |
| q10 | 1/2/5/2 | 2/2/5/2 | **Variant +1** | +1 | Slightly better abstention |

**Critical Issue - q09 (ERR-403-AUTH):**
```
Baseline: "Tôi không biết" (Abstained correctly, gave up)
  → Faithfulness: 5, Relevance: 5 (correct abstention)

Variant: "Tôi không biết" (Also abstained but...)
  → Faithfulness: 1, Relevance: 1 (Scored as failure to answer!)
  → Root cause: Rerank selected wrong chunks, answer was incoherent
  → Impact: -4 points swing on one question
```

**Nhận xét:**
Variant 1 (Hybrid + Rerank) **không cải thiện** RAG pipeline, mà **tệ hơn** baseline:
- ❌ Faithfulness giảm (-0.20): Hybrid fusion dilutes dense signal
- ❌ Relevance giảm (-0.40): Rerank không giúp tìm giải pháp tốt hơn
- ❌ Completeness giảm (-0.30): Complex policy questions cần dense semantic, không BM25 keyword
- 🔴 **Critical**: q09 regression (-4 points) - Variant broke a working case

**Kết luận:**
> **BASELINE WINS**: Hybrid + Rerank variant **rejected**. Performance degradation -0.23 points (-5% vs baseline).

**Lý do:**
1. Dense embedding already captures policy semantics well (Relevance 4.70/5)
2. BM25 keyword search adds noise (interference for policy documents)
3. Rerank model (MS-MARCO) tuned for web search, not policy Q&A
4. Cross-encoder inference slows pipeline without quality gain

**Recommendation:**
Keep Baseline (Dense-only) for production. Future optimizations should focus on:
- Improving chunking for complex policies (q04, q07)
- Better prompting for completeness (policy exceptions)
- Document out-of-domain cases (q09, q10) requiring data augmentation

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > **Incomplete completeness on complex policies** (score 2-3/5 on q04, q07)
   > 
   > Root cause: Chunking strategy loses policy structure. Solution: Implement hierarchical indexing (section-level summary + detail chunks)

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > **Retrieval strategy** có tác động TIÊU CỰC khi sử dụng Hybrid. 
   > 
   > Evidence: Dense-only baseline 4.53/5 >> Hybrid+Rerank 4.30/5
   > 
   > Insight: Dense embedding là đủ tốt; thêm complexity (BM25 + rerank) làm tệ hơn

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > **Option A**: Query-aware chunk selection (dense retrieve top-10, rerank to top-3 before LLM)
   > 
   > **Option B**: Hierarchy 2-layer indexing (summary chunks + detail chunks)
   > 
   > **Option C**: Prompt engineering for completeness (add "list all exceptions" to system prompt)
   > 
   > **Recommended**: Option A (simpler, more likely to improve without breaking)

---

## Final Summary

| Phase | Date | Config | Score | Status |
|-------|------|--------|-------|--------|
| Sprint 1: Index | 2026-04-13 | 29 chunks, 5 docs | N/A | Complete |
| Sprint 2: Dense Baseline | 2026-04-13 | Dense retrieval | **4.53/5** | **BASELINE** |
| Sprint 3: Hybrid+Rerank | 2026-04-13 | Hybrid + rerank | **4.30/5** | **REJECTED** |
| Sprint 4: Evaluation | 2026-04-13 | A/B comparison | Delta -0.23 | Complete |

**Winner: BASELINE (Dense-only)**  
**Reason: -5% penalty for added complexity without quality gain**  
**Next: Focus on prompt engineering for completeness improvement**

