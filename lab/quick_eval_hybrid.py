"""
quick_eval_hybrid.py — Fast evaluation of Hybrid variant only
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from rag_answer import rag_answer

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"

def score_faithfulness(answer: str, expected: str, chunks_text: str) -> int:
    """Simple faithfulness scoring"""
    expected_keywords = expected.lower().split()
    chunks_lower = chunks_text.lower()
    
    if not answer or "không" in answer.lower() or "không biết" in answer.lower():
        return 3
    
    matched_keywords = sum(1 for kw in expected_keywords if len(kw) > 3 and kw in chunks_lower)
    match_ratio = matched_keywords / max(len(expected_keywords), 1)
    
    if match_ratio >= 0.8:
        return 5
    elif match_ratio >= 0.6:
        return 4
    elif match_ratio >= 0.4:
        return 3
    elif match_ratio >= 0.2:
        return 2
    else:
        return 1

def score_relevance(answer: str, query: str, expected: str) -> int:
    answer_lower = answer.lower()
    expected_lower = expected.lower()
    
    if "không" in answer_lower or "không biết" in answer_lower:
        if "không" in expected_lower:
            return 5
        else:
            return 2
    
    expected_terms = [t for t in expected_lower.split() if len(t) > 3]
    matched = sum(1 for term in expected_terms if term in answer_lower)
    match_ratio = matched / max(len(expected_terms), 1)
    
    if match_ratio >= 0.7:
        return 5
    elif match_ratio >= 0.5:
        return 4
    elif match_ratio >= 0.3:
        return 3
    elif match_ratio >= 0.1:
        return 2
    else:
        return 1

def score_completeness(answer: str, expected: str) -> int:
    answer_lower = answer.lower()
    expected_lower = expected.lower()
    
    if "không" in answer_lower or "không biết" in answer_lower:
        if "không" in expected_lower:
            return 5
        else:
            return 2
    
    expected_phrases = [p.strip() for p in expected_lower.replace(".", "").replace(",", "").split("\n") if len(p.strip()) > 5]
    matched_phrases = sum(1 for phrase in expected_phrases if phrase in answer_lower or any(w in answer_lower for w in phrase.split()[:3]))
    
    if len(expected_phrases) == 0:
        return 3
    
    match_ratio = matched_phrases / len(expected_phrases)
    
    if match_ratio >= 0.9:
        return 5
    elif match_ratio >= 0.7:
        return 4
    elif match_ratio >= 0.5:
        return 3
    elif match_ratio >= 0.2:
        return 2
    else:
        return 1

def score_context_recall(sources: List[str], expected_sources: List[str]) -> int:
    if not expected_sources:
        return 3 if sources else 2
    
    sources_normalized = [s.lower().replace("\\", "/") for s in sources]
    expected_normalized = [s.lower().replace("\\", "/") for s in expected_sources]
    
    matched = sum(1 for exp in expected_normalized 
                  if any(exp in src or src in exp for src in sources_normalized))
    
    if matched == len(expected_normalized):
        return 5
    elif matched >= len(expected_normalized) * 0.8:
        return 4
    elif matched >= len(expected_normalized) * 0.6:
        return 3
    elif matched >= len(expected_normalized) * 0.3:
        return 2
    else:
        return 1

def run_variant_evaluation():
    """Test Hybrid variant"""
    print("Testing Hybrid Variant (Dense + BM25)...", flush=True)
    
    with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
        test_data_raw = json.load(f)
    
    if isinstance(test_data_raw, list):
        test_questions = test_data_raw
    else:
        test_questions = test_data_raw.get("questions", [])
    
    results = []
    
    for i, item in enumerate(test_questions[:10], 1):
        query = item["question"]
        expected_answer = item["expected_answer"]
        expected_sources = item.get("expected_sources", [])
        
        print(f"\n[{i}/10] Q: {query[:60]}...", flush=True)
        
        try:
            # Test Hybrid
            result = rag_answer(
                query,
                retrieval_mode="hybrid",
                top_k_search=10,
                top_k_select=3,
                use_rerank=False,
                verbose=False
            )
            
            answer = result["answer"]
            sources = result["sources"]
            chunks_used = result["chunks_used"]
            chunks_text = "\n".join([c["text"] for c in chunks_used])
            
            # Score
            f_score = score_faithfulness(answer, expected_answer, chunks_text)
            r_score = score_relevance(answer, query, expected_answer)
            c_score = score_completeness(answer, expected_answer)
            cr_score = score_context_recall(sources, expected_sources)
            
            print(f"    F:{f_score} R:{r_score} C:{c_score} CR:{cr_score}", flush=True)
            
            results.append({
                "id": item.get("id", ""),
                "query": query,
                "expected_answer": expected_answer,
                "answer": answer,
                "sources": sources,
                "scores": {
                    "faithfulness": f_score,
                    "relevance": r_score,
                    "completeness": c_score,
                    "context_recall": cr_score,
                },
            })
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
            results.append({
                "id": item.get("id", ""),
                "query": query,
                "error": str(e),
                "scores": {"faithfulness": 1, "relevance": 1, "completeness": 1, "context_recall": 1},
            })
    
    return results

def generate_scorecard_hybrid(results: List[Dict[str, Any]]) -> str:
    """Generate scorecard for hybrid"""
    scorecard = f"""# Scorecard: Variant - Hybrid (Dense + BM25)

**Timestamp:** {datetime.now().isoformat()}  
**Configuration:** variant_hybrid  
**Total Questions Evaluated:** {len(results)}

---

## Summary Metrics

| Metric | Average Score | Details |
|--------|--------------|---------|
| **Faithfulness** | {sum(r['scores']['faithfulness'] for r in results) / len(results):.2f}/5 | Answer grounded in context |
| **Relevance** | {sum(r['scores']['relevance'] for r in results) / len(results):.2f}/5 | Query answered correctly |
| **Completeness** | {sum(r['scores']['completeness'] for r in results) / len(results):.2f}/5 | All aspects covered |
| **Context Recall** | {sum(r['scores']['context_recall'] for r in results) / len(results):.2f}/5 | Retrieved necessary sources |
| **Overall Average** | {sum(sum(r['scores'].values()) for r in results) / (len(results) * 4):.2f}/5 | Combined score |

---

## Detailed Results

| # | Query | Answer | F | R | Co | CR |
|---|-------|--------|---|---|----|----|  
"""
    
    for i, result in enumerate(results, 1):
        query_short = result["query"][:40].replace("\n", " ")
        answer_short = result["answer"][:40].replace("\n", " ") if "answer" in result else "ERROR"
        f = result["scores"]["faithfulness"]
        r = result["scores"]["relevance"]
        co = result["scores"]["completeness"]
        cr = result["scores"]["context_recall"]
        
        scorecard += f"| {i} | {query_short}... | {answer_short}... | {f} | {r} | {co} | {cr} |\n"
    
    scorecard += "\n---\n\n## Legend\n- **F** = Faithfulness\n- **R** = Relevance\n- **Co** = Completeness\n- **CR** = Context Recall\n"
    
    return scorecard

if __name__ == "__main__":
    print("="*70)
    print("HYBRID VARIANT EVALUATION")
    print("="*70)
    
    results = run_variant_evaluation()
    
    # Save results
    with open(RESULTS_DIR / "raw_variant_hybrid.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\n✅ Saved raw results")
    
    # Generate scorecard
    scorecard = generate_scorecard_hybrid(results)
    with open(RESULTS_DIR / "scorecard_variant_hybrid.md", "w", encoding="utf-8") as f:
        f.write(scorecard)
    print("✅ Scorecard saved")
    
    print("\n" + "="*70)
    print("EVALUATION COMPLETE")
    print("="*70)
