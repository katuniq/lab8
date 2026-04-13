# 👥 Phân Công Nhiệm Vụ - LAB 08: RAG Pipeline

**Nhóm:** 22  
**Deadline:** 2026-04-13 18:00  
**Status:** ✅ Complete

---

## 📋 Danh Sách Thành Viên & Nhiệm Vụ

| STT | Họ Tên | mSSV | Vai Trò | Task Chính |
|-----|--------|------|--------|-----------|
| 1 | Trần Quốc Khánh | 2A202600306 | Lead | Sprint 1 (Index) | 
| 2 | Nguyễn Xuân Tùng | 2A202600247 | Retrival Owner | Sprint 2 (Retrieval) |
| 3 | Nguyễn Công Thành | 2A202600142 | Eval Owner | Sprint 4 (Evaluation) |
| 4 | Nguyễn Viết Hùng | 2A202600240 | Tuning Owner | Sprint 3 (Tuning) |
| 5 | Đỗ Đình Hoàn | 2A202600036 | Documentation Owner | Docs Modify and Test |

---

## 📝 Chi Tiết Task

### 👤 Người 1: Trần Quốc Khánh (2A202600306) - Sprint 1 Lead
**Vai trò:** Index Builder & Technical Lead

**Task Chính:**
- ✅ Sprint 1 (60 phút): Implement `index.py`
  - Đọc 5 documents từ `data/docs/`
  - Tách chunk (400 tokens, 50 tokens overlap)
  - Extract metadata (source, section, department, effective_date, access)
  - Embed với OpenAI text-embedding-3-small
  - Lưu 29 chunks vào ChromaDB (persistent)
  

---

### 👤 Người 2: Nguyễn Xuân Tùng (2A202600247) - Sprint 2 Retrieval Owner
**Vai trò:** Backend Developer & Retrieval Specialist

**Task Chính:**
- ✅ Sprint 2 (60 phút): Implement retrieval + LLM layer
  - Implement `retrieve_dense()` - ChromaDB cosine similarity search
    - Query embedding sử dụng text-embedding-3-small
    - Return top 10 candidates với score (1 - distance)
  - Implement `call_llm()` - OpenAI API (gpt-4o-mini)
    - System prompt tiếng Việt với grounding requirement
    - Temperature = 0 (deterministic)
    - Citation format: [1][2] v.v.
  - Implement `rag_answer()` - Main RAG pipeline
    - Tích hợp retrieve_dense() + call_llm()
    - Output format: {answer, sources, chunks_used, config}
  - Test end-to-end: index → retrieve → answer

---

### 👤 Người 3: Nguyễn Công Thành (2A202600142) - Sprint 4 Eval Owner
**Vai trò:** Quality Assurance & Evaluation Lead

**Task Chính:**
- ✅ Sprint 4 (60 phút): Implement evaluation framework
  - Implement 4 scoring metrics:
    - `score_faithfulness()` - Check keyword overlap: answer_keywords ∩ source_keywords
    - `score_relevance()` - Term matching: expected_answer_terms in generated_answer
    - `score_completeness()` - Aspect coverage: matched_aspects / total_aspects
    - `score_context_recall()` - Source matching: expected_sources ⊆ retrieved_sources
  
  - Create evaluation scripts:
    - `quick_eval_hybrid.py` - Fast variant testing (10 questions)
    - `run_evaluation.py` - Full config comparison
  
  - Evaluate both configs on 10 test questions:
    - Baseline (Dense): 4.20/5 ⭐
    - Variant (Hybrid): 4.08/5
  
  - Generate evaluation outputs:
    - `scorecard_baseline_dense.md` (metrics table)
    - `scorecard_variant_hybrid.md` (metrics table)
    - `raw_baseline_dense.json` (full Q&A data)
    - `raw_variant_hybrid.json` (full Q&A data)

---

### 👤 Người 4: Nguyễn Viết Hùng (2A202600240) - Sprint 3 Tuning Owner
**Vai trò:** Tuning & Optimization Lead

**Task Chính:**
- ✅ Sprint 3 (60 phút): Implement + test tuning variants
  - Implement `retrieve_sparse()` - BM25 keyword search
  - Implement `retrieve_hybrid()` - Dense + BM25 with RRF fusion
    - Dense weight: 0.6 (semantic)
    - Sparse weight: 0.4 (keyword)
    - RRF formula: 0.6/(60 + dense_rank) + 0.4/(60 + sparse_rank)
  - Implement `rerank()` - Cross-encoder optional
  - Test variant: Hybrid on 10 questions
  - Compare: Baseline (4.20/5) vs Hybrid (4.08/5)
  - Decide: Baseline better (+0.12), reject Hybrid

---

### 👤 Người 5: Đỗ Đình Hoàn (2A202600036) - Documentation Owner
**Vai trò:** Documentation & Reporting Lead

**Task Chính:**

**Before 18:00 (Documentation):**
- ✅ `docs/tuning-log.md` (Sprint 3 decisions)
  - Giải thích lựa chọn các variant
  - Tại sao chọn Hybrid để test
  - Kết quả so sánh Baseline vs Hybrid
  - Recommendation: Baseline chosen
  
- ✅ `docs/architecture.md` (System architecture documentation)
  - Overview của toàn bộ RAG pipeline (4 sprints)
  - Implementation details từ mỗi sprint
  - Performance metrics và comparison results (Baseline: 4.20/5 vs Hybrid: 4.08/5)
  - Final recommendation: Baseline selected

**After 18:00 (Reports):**
- 📋 `reports/group_report.md` (Group summary)
  - Phân công công việc
  - Timeline: Sprint 1-4 execution
  - Kết quả cuối cùng
  - Kết luận & khuyến nghị


---