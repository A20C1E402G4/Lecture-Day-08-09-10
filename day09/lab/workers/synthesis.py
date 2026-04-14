"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

import io
# Safe UTF-8 encoding for Windows console
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    except (AttributeError, io.UnsupportedOperation):
        pass

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý IT Helpdesk nội bộ của VinAI.

Quy tắc nghiêm ngặt:
1. CHỈ trả lời dựa vào context được cung cấp. KHÔNG dùng kiến thức ngoài.
2. Trích dẫn nguồn cuối mỗi câu quan trọng dưới định dạng: [tên_file].
3. Nếu context không đủ thông tin, hãy nói rõ: "Không tìm thấy thông tin chính xác trong tài liệu nội bộ".
4. Ưu tiên sự chính xác và súc tích.
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    # Option A: OpenAI
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.1,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ OpenAI synthesis failed: {e}")

    # Fallback: trả về message báo lỗi
    return "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."


def _build_context(chunks: list, policy_result: dict, mcp_tools_used: list = []) -> str:
    """Xây dựng context string từ chunks, policy và MCP tools."""
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO (ChromaDB) ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            parts.append(f"[{i}] Nguồn: {source}\nNội dung: {text}")

    if policy_result and policy_result.get("exceptions_found"):
        parts.append("\n=== CÁC NGOẠI LỆ CHÍNH SÁCH CẦN LƯU Ý ===")
        for ex in policy_result["exceptions_found"]:
            parts.append(f"- {ex.get('rule', '')} (Nguồn: {ex.get('source', '')})")

    if mcp_tools_used:
        parts.append("\n=== DỮ LIỆU TỪ HỆ THỐNG PHỤ TRỢ (MCP Tools) ===")
        for tool in mcp_tools_used:
            tool_name = tool.get("tool", "unknown")
            output = tool.get("output", {})
            parts.append(f"[MCP: {tool_name}] Kết quả: {json.dumps(output, ensure_ascii=False)}")

    if not parts:
        return "(Không có thông tin tham khảo)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict, mcp_tools_used: list = []) -> float:
    """
    Ước tính confidence dựa trên evidence và tools.
    """
    if not chunks and not mcp_tools_used:
        return 0.1

    if "Không tìm thấy thông tin" in answer:
        return 0.2

    # Điểm cơ bản từ retrieval
    avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks) if chunks else 0.5
    
    # Cộng thêm điểm nếu có dữ liệu thực từ MCP
    mcp_bonus = 0.2 if mcp_tools_used else 0

    confidence = min(0.98, avg_score + mcp_bonus)
    return round(confidence, 2)


def synthesize(task: str, chunks: list, policy_result: dict, mcp_tools_used: list = []) -> dict:
    """
    Tổng hợp câu trả lời từ chunks, policy và MCP context.
    """
    context = _build_context(chunks, policy_result, mcp_tools_used)

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi của người dùng: {task}

Dữ liệu hỗ trợ:
{context}

Dựa trên dữ liệu trên, hãy trả lời câu hỏi của người dùng một cách chuyên nghiệp nhất."""
        }
    ]

    answer = _call_llm(messages)
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(chunks, answer, policy_result)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})
    mcp_tools_used = state.get("mcp_tools_used", [])

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
            "mcp_calls": len(mcp_tools_used),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result, mcp_tools_used)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] logic complete. confidence={result['confidence']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    # Mock test 1
    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1 được xử lý trong 4 giờ làm việc kể từ lúc tiếp nhận.",
                "source": "sla_p1_2026.txt",
                "score": 0.95,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\n>> Answer:\n{result['final_answer']}")
    print(f"Confidence: {result['confidence']}")

    print("\n✅ synthesis_worker test done.")
