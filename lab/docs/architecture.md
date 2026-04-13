# Architecture — RAG Pipeline (Day 08 Lab)

> Template: Điền vào các mục này khi hoàn thành từng sprint.
> Deliverable của Documentation Owner.

## 1. Tổng quan kiến trúc

```
[Raw Docs]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[ChromaDB Vector Store]
    ↓
[rag_answer.py: Query → Retrieve → Rerank → Generate]
    ↓
[Grounded Answer + Citation]
```

**Mô tả ngắn gọn:**
> RAG (Retrieval-Augmented Generation) pipeline xử lý các câu hỏi về chính sách công ty (HR, IT, CS) bằng cách tìm kiếm tài liệu liên quan thông qua dense embedding, sau đó truyền context cho LLM để sinh câu trả lời có trích dẫn. Hệ thống giúp nhân viên nhanh chóng tìm kiếm thông tin chính xác từ các tài liệu nội bộ mà không cần đọc toàn bộ tài liệu.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|----------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 11 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 7 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 3 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 2 |
| **Tổng cộng** | **5 documents** | **Covered** | **29 chunks** |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens | Balanced: long enough for context, short enough for retrieval precision |
| Overlap | 50 tokens | Preserve continuity across chunk boundaries |
| Chunking strategy | Paragraph-based splitting with section preservation | Maintains policy structure without cutting mid-requirement |
| Metadata fields | source, section, department, effective_date, access | Enable filtering by document version, source citation, and access control |
| **Metadata coverage** | **100%** | All 29 chunks have effective_date (no missing values) |

### Embedding model
- **Model**: OpenAI `text-embedding-3-small` (1536 dimensions, multilingual)
- **Vector store**: ChromaDB (PersistentClient with local persistence at `chroma_db/`)
- **Similarity metric**: Cosine (default for dense embeddings)

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|--------|
| Strategy | Dense embedding similarity (ChromaDB cosine) |
| Top-k search | 10 |
| Top-k select | 3 (after semantic relevance sorting) |
| Rerank | No |
| **Overall Score** | **4.53/5** |
| Faithfulness | 4.40/5 |
| Relevance | 4.70/5 |
| Context Recall | 5.00/5 (perfect) |
| Completeness | 4.00/5 |

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
| Strategy | **Hybrid (60% Dense + 40% BM25 sparse)** | Dense → Hybrid with RRF |
| Top-k search | 10 | Same |
| Top-k select | 3 | Same (after rerank) |
| Rerank | **Yes (Cross-encoder MS-MARCO)** | No → Yes |
| Query transform | None | N/A |
| **Overall Score** | **4.30/5** | **-0.23 (-5%)** |
| Faithfulness | 4.20/5 | -0.20 |
| Relevance | 4.30/5 | -0.40 |
| Context Recall | 5.00/5 | 0 |
| Completeness | 3.70/5 | -0.30 |

**Lý do thử variant này:**
> Hypothesis: Dense embedding alone might miss keyword queries (error codes like ERR-403-AUTH). Hybrid retrieval (BM25 + semantic) could capture both natural language and technical terms. Cross-encoder rerank could refine selection.

**Kết luận: VARIANT REJECTED**
> Performance degradation -5% vs baseline. Root cause:
> - BM25 keyword matching introduces noise for policy documents (semantic-heavy corpus)
> - Cross-encoder tuned for web search (MS-MARCO), not policy Q&A
> - q09 failure: Variant scored 1 vs baseline 5 on out-of-domain query
> - **Keep baseline (Dense-only) for production**

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context is insufficient, say you do not know.
Cite the source field when possible.
Keep your answer short, clear, and factual.

Question: {query}

Context:
[1] {source} | {section} | score={score}
{chunk_text}

[2] ...

Answer:
```

### LLM Configuration
| Tham số | Giá trị | Lý do |
|---------|--------|-------|
| Model | OpenAI `gpt-4o-mini` | Fast, cost-effective, multilingual Vietnamese support |
| Temperature | 0 | Deterministic output for consistent evaluation scoring |
| Max tokens | 512 | Sufficient for policy Q&A (avg 150-300 tokens) |
| System prompt | "Answer only from retrieved context. If insufficient, abstain." | Enforce grounding, prevent hallucination |

---

## 5. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra |
|-------------|-------------|---------------|
| Index lỗi | Retrieve về docs cũ / sai version | `inspect_metadata_coverage()` trong index.py |
| Chunking tệ | Chunk cắt giữa điều khoản | `list_chunks()` và đọc text preview |
| Retrieval lỗi | Không tìm được expected source | `score_context_recall()` trong eval.py |
| Generation lỗi | Answer không grounded / bịa | `score_faithfulness()` trong eval.py |
| Token overload | Context quá dài → lost in the middle | Kiểm tra độ dài context_block |

---

## 7. Evaluation Results (Sprint 4)

### Summary: Baseline Wins
| Metric | Baseline | Variant | Winner |
|--------|----------|---------|--------|
| **Overall** | **4.53/5** | **4.30/5** | Baseline |
| Faithfulness | 4.40/5 | 4.20/5 | Baseline |
| Relevance | 4.70/5 | 4.30/5 | Baseline |
| Context Recall | 5.00/5 | 5.00/5 | Tie |
| Completeness | 4.00/5 | 3.70/5 | Baseline |

### Key Insights
**Strengths of Baseline (Dense-only):**
- Perfect context recall (5.00/5) - retrieves all expected sources
- Best relevance (4.70/5) - semantic embeddings align well with policy queries
- Good faithfulness (4.40/5) - model grounds answers in context

**Failure Modes (affecting both baseline & variant):**
- q07: Completeness=2/5 (answer too generic for "Approval Matrix")
- q10: Faithfulness=1/5, Relevance=2/5 (VIP refund process not in corpus)
- q09: Variant catastrophically failed (1 vs 5 faithfulness) on error code query

**Why Variant Failed:**
1. BM25 hybrid fusion dilutes dense semantic signal for policy corpus
2. Cross-encoder (MS-MARCO) optimized for web search, not enterprise Q&A
3. Increased complexity without quality gain (added inference latency)

### Recommendation
**Keep Baseline (Dense-only) as production configuration.**

For future improvements (if time permits):
- A: Query-aware chunk selection (dense retrieve top-10 → lightweight rerank)
- B: Hierarchical indexing (summary chunks + detail chunks)
- C: Prompt engineering for completeness (explicit instruction for exceptions)

---

## 8. Diagram

```
[Raw Docs]
    ↓
[Preprocessor: Split by paragraphs]
    ↓
[Chunker: 400 tokens + 50 overlap]
    ↓
[Embedding: text-embedding-3-small]
    ↓
[ChromaDB: Store vectors + metadata]
    ↓
======== QUERY TIME ========
    ↓
[User Query: Vietnamese text]
    ↓
[Embed query: text-embedding-3-small]
    ↓
[Vector search: Cosine similarity]
    ↓
[Select top-3]
    ↓
[Build context block with citations]
    ↓
[GPT-4o-mini (temp=0)]
    ↓
[Grounded Answer + [Source]]
```

---

## 9. Deployment Checklist

- [x] Index built: 29 chunks, all documents processed
- [x] Metadata complete: 100% effective_date coverage
- [x] Baseline evaluated: 4.53/5 average
- [x] Variant tested & rejected: -5% performance
- [x] Grading scores logged: `logs/grading_run.json`
- [x] Configuration decided: Dense baseline selected
- [ ] Manual completeness review for q04, q07, q10 (optional)
- [ ] Production deployment
