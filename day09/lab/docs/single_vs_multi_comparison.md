# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** ___________  
**Ngày:** ___________

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Điền vào bảng sau. Lấy số liệu từ:
> - Day 08: chạy `python eval.py` từ Day 08 lab
> - Day 09: chạy `python eval_trace.py` từ lab này

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ~0.7 | 0.8 | +0.1 | |
| Avg latency (ms) | ~4000 | 7898 | +3898 | Do chạy nhiều node LLM |
| Abstain rate (%) | 0% | 0% | 0 | |
| Multi-hop accuracy | 3.0/5 | 4.5/5 | +1.5 | Cải thiện nhờ Policy Worker |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Dễ dàng debug |
| Debug time (estimate) | 20 phút | 5 phút | -15 | Chỉ cần xem trace log |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Cao | Cao |
| Latency | Thấp (~4s) | Cao (~8s) |
| Observation | Đủ dùng | Chậm hơn nhưng an toàn hơn |

**Kết luận:** Multi-agent không mang lại nhiều lợi ích cho câu hỏi đơn giản, thậm chí làm tăng độ trễ.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Trung bình (cụt ý) | Cao (nhờ Policy Node) |
| Routing visible? | ✗ | ✓ |
| Observation | Hay quên ý ở doc thứ 2 | Kết hợp tốt thông tin chéo |

**Kết luận:** Multi-agent vượt trội trong việc xử lý các yêu cầu phức tạp cần kết hợp nhiều quy trình.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 20 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 5 phút
```

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm 1 worker mới |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa retrieval_worker độc lập |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker |

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 2 LLM calls |
| Complex query | 1 LLM call | 3 LLM calls |
| MCP tool call | N/A | 1 Tool Call |

---

## 6. Kết luận

1. Multi-agent giúp kiểm soát luồng xử lý tốt hơn, đặc biệt là các yêu cầu nhạy cảm cần check Policy.
2. Khả năng quan sát (Observability) qua Trace giúp rút ngắn thời gian debug từ 20p xuống 5p.

**Multi-agent kém hơn ở điểm sau:**
1. Độ trễ cao và chi phí LLM tăng gấp 2-3 lần.

**Khi nào KHÔNG nên dùng multi-agent?**
Khi chỉ cần tra cứu thông tin tĩnh, đơn giản và yêu cầu thời gian phản hồi cực nhanh.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Thêm tính năng tự động sửa lỗi (Self-correction) nếu Synthesis phát hiện câu trả lời không khớp với context ban đầu.
