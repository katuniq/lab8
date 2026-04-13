# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Đình Hoàn  
**mSSV:** 2A202600036  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13 18:00  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi là Documentation Owner, chủ yếu tập trung vào việc tài liệu hóa toàn bộ RAG pipeline. Công việc chính của tôi bao gồm:

**Before 18:00:**
- Viết `docs/tuning-log.md`: Tài liệu quyết định tuning, so sánh 3 variant (Dense, Sparse, Hybrid). Giải thích tại sao chọn Hybrid để test và kết quả cuối cùng: Baseline (4.20/5) thắng Hybrid (4.08/5).
- Viết `docs/architecture.md`: Tài liệu kiến trúc hệ thống, mô tả 4 sprints từ indexing (29 chunks), retrieval (dense + LLM), tuning (RRF hybrid), đến evaluation (4 metrics). Bao gồm metrics chi tiết, root cause analysis, và recommendation cuối cùng.

**Kết nối:** Công việc của tôi dựa trên kết quả từ các thành viên khác (Người 1-4), sau đó thành cơ sở cho báo cáo nhóm.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

**Hybrid Retrieval & RRF Fusion:** Ban đầu tôi nghĩ kết hợp Dense + Sparse sẽ luôn tốt hơn, nhưng kết quả cho thấy không phải lúc nào cũng đúng. Hybrid (RRF: 60% dense, 40% sparse) chỉ đạt 4.08/5, thấp hơn Dense thuần (4.20/5). Điều này dạy tôi rằng:
- Không phải tất cả kết hợp đều tạo ra emergent properties
- Thêm keyword search (BM25) không giúp nếu Dense đã capture semantic tốt
- Evaluation metrics là cách duy nhất để verify assumptions

**Metrics-Driven Decision Making:** 4 metrics (Faithfulness, Relevance, Completeness, Context Recall) giúp tôi justify tại sao chọn Baseline thay vì Hybrid dựa trên dữ liệu, không phải intuition.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Ngạc nhiên:**
- Hybrid retrieval KHÔNG cải thiện scores dù dự kiến sẽ thế. Baseline (Dense) đã khá tốt rồi (F:2.60, R:4.40, Co:5.00, CR:4.80 = 4.20/5).
- Relevance score cao (4.40 → 4.00 với Hybrid) nhưng Faithfulness thấp (2.60 → 2.50). Điều này cho thấy Dense tìm context tốt hơn nhưng LLM có xu hướng hallucinate.

**Khó khăn:**
- Phải đồng bộ tài liệu từ 4 sprints khác nhau vào 1 architecture doc mà vẫn rõ ràng
- Challenge lớn là refactor tài liệu sau khi các sprint hoàn thành, vì mỗi người có style khác nhau

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "Nhân viên mới được phép truy cập hệ thống nào mà không cần approval?" (Từ `access_control_sop.txt`)

**Phân tích:**

Câu hỏi này là một trong những thách thách nhất trong dataset:
- **Baseline score:** Faithfulness 2/5, Relevance 4/5, Completeness 5/5, Context Recall 4/5 → **3.75/5**
- **Lỗi:** Baseline trả lời đúng về hệ thống nào CÓ thể truy cập, nhưng không capture được "mà không cần approval" - điều này cần kiến thức ngôn ngữ tốt hơn

**Nguyên nhân:**
1. **Indexing:** Document `access_control_sop.txt` có đoạn "nhân viên mới bằng default có access: email, intranet" nhưng không chunk rõ ràng hệ thống NÀO là self-service vs NÀO cần approval
2. **Retrieval (Dense):** Tìm ra đúng context nhưng ranking không optimal (top-1 không phải câu trả lời chính)
3. **Generation:** LLM phần nào trả lời nhưng thiếu nuance về "không cần approval"

**Hybrid có cải thiện không:**
- Không! Hybrid (4.00 relevance) còn tệ hơn Baseline (4.40 relevance). RRF làm "blur" signal vì BM25 ưu tiên keyword match chứ không hiểu semantic của "approval requirement"

**Kết luận:** Câu hỏi này cần pre-processing tốt hơn hoặc advanced indexing strategy, không phải chỉ hybrid retrieval.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Implement hierarchical indexing:** Thay vì chunk 400 tokens, tôi sẽ index 2 level: section-level summary + detail chunks. Điều này sẽ giúp Dense retrieval rank better vì context rõ ràng hơn.

2. **Add policy index:** Tạo thêm index cho các "policy rules" extracted từ documents (ví dụ: "rule: new_employee.access = [email, intranet]"). Hybrid lúc đó sẽ hữu dụng vì có thể match keyword "approval" tốt hơn.

Dự kiến: 2 cải tiến này có thể nâng score từ 4.20 → 4.50+

---
