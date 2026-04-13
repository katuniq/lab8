"""
run_evaluation.py — Complete evaluation pipeline for Sprint 3 & 4

Chạy baseline và variants, so sánh metrics, generate scorecards.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from rag_answer import rag_answer

# =============================================================================
# CONFIGURATIONS
# =============================================================================

TEST_QUESTIONS_PATH = Path(__file__).parent / "data" / "test_questions.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Define configurations to test
CONFIGS = {
    "baseline_dense": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "label": "Baseline (Dense Only)",
    },
    "variant_hybrid": {
        "retrieval_mode": "hybrid",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": False,
        "label": "Variant: Hybrid (Dense + BM25)",
    },
    "variant_rerank": {
        "retrieval_mode": "dense",
        "top_k_search": 10,
        "top_k_select": 3,
        "use_rerank": True,
        "label": "Variant: Dense + Rerank",
    },
}

# =============================================================================
# EVALUATION METRICS (Simple manual scoring)
# =============================================================================

def score_faithfulness(answer: str, expected: str, chunks_text: str) -> int:
    """
    Faithfulness (1-5): Is answer grounded in retrieved chunks?
    
    5: All information in answer is in retrieved chunks
    4: Mostly grounded, 1 minor detail unverified
    3: Partially grounded, some model knowledge
    2: Much information not in chunks
    1: Mostly fabricated
    """
    # Simple heuristic: check if expected answer content is in retrieved chunks
    expected_keywords = expected.lower().split()
    chunks_lower = chunks_text.lower()
    
    if not answer or "không" in answer.lower() or "không biết" in answer.lower():
        return 3  # Abstain is neutral
    
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
    """
    Relevance (1-5): Does answer address the query?
    
    5: Directly answers query
    4: Answers query with minor irrelevance
    3: Partially relevant
    2: Weakly relevant
    1: Irrelevant
    """
    answer_lower = answer.lower()
    query_lower = query.lower()
    expected_lower = expected.lower()
    
    if "không" in answer_lower or "không biết" in answer_lower:
        # Check if it's appropriate to abstain (query not answerable)
        if "không" in expected_lower:
            return 5
        else:
            return 2
    
    # Check if answer contains key terms from expected
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
    """
    Completeness (1-5): Does answer cover all key aspects?
    
    5: Fully answers all aspects
    4: Answers main query, misses one detail
    3: Answers partial query
    2: Answers small part
    1: Doesn't answer at all
    """
    answer_lower = answer.lower()
    expected_lower = expected.lower()
    
    if "không" in answer_lower or "không biết" in answer_lower:
        if "không" in expected_lower:
            return 5
        else:
            return 2
    
    # Split expected into key phrases (sentences, numbers, dates)
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
    """
    Context Recall (1-5): Did we retrieve all necessary documents?
    
    5: Retrieved all expected sources
    4: Retrieved most expected sources
    3: Retrieved half
    2: Retrieved few
    1: Missed all
    """
    if not expected_sources:
        # If no expected sources, score based on whether we abstained correctly
        return 3 if sources else 2
    
    # Normalize source names
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


# =============================================================================
# RUN EVALUATION
# =============================================================================

def run_evaluation(config: Dict[str, Any], verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Run evaluation for a given configuration on all test questions.
    
    Returns list of results: [{"query": ..., "answer": ..., "scores": {...}}, ...]
    """
    with open(TEST_QUESTIONS_PATH, encoding="utf-8") as f:
        test_data_raw = json.load(f)
    
    # Handle both list and dict formats
    if isinstance(test_data_raw, list):
        test_questions = test_data_raw
    else:
        test_questions = test_data_raw.get("questions", [])
    
    results = []
    
    for item in test_questions[:10]:  # Top 10 questions
        query = item["question"]
        expected_answer = item["expected_answer"]
        expected_sources = item.get("expected_sources", [])
        
        if verbose:
            print(f"\n[{config['label']}]")
            print(f"Q: {query[:60]}...")
        
        try:
            # Run RAG pipeline
            rag_result = rag_answer(
                query,
                retrieval_mode=config["retrieval_mode"],
                top_k_search=config["top_k_search"],
                top_k_select=config["top_k_select"],
                use_rerank=config["use_rerank"],
                verbose=False
            )
            
            answer = rag_result["answer"]
            sources = rag_result["sources"]
            chunks_used = rag_result["chunks_used"]
            
            # Combine chunk texts for faithfulness scoring
            chunks_text = "\n".join([c["text"] for c in chunks_used])
            
            # Calculate scores
            faithfulness = score_faithfulness(answer, expected_answer, chunks_text)
            relevance = score_relevance(answer, query, expected_answer)
            completeness = score_completeness(answer, expected_answer)
            context_recall = score_context_recall(sources, expected_sources)
            
            if verbose:
                print(f"A: {answer[:60]}...")
                print(f"Scores → Faithfulness: {faithfulness}, Relevance: {relevance}, Completeness: {completeness}, Context: {context_recall}")
            
            results.append({
                "id": item.get("id", ""),
                "query": query,
                "expected_answer": expected_answer,
                "expected_sources": expected_sources,
                "answer": answer,
                "sources": sources,
                "scores": {
                    "faithfulness": faithfulness,
                    "relevance": relevance,
                    "completeness": completeness,
                    "context_recall": context_recall,
                },
            })
        
        except Exception as e:
            print(f"Error processing query: {e}")
            results.append({
                "id": item.get("id", ""),
                "query": query,
                "expected_answer": expected_answer,
                "error": str(e),
                "scores": {
                    "faithfulness": 1,
                    "relevance": 1,
                    "completeness": 1,
                    "context_recall": 1,
                },
            })
    
    return results


# =============================================================================
# GENERATE SCORECARDS
# =============================================================================

def generate_scorecard(results: List[Dict[str, Any]], config_name: str, config: Dict[str, Any]) -> str:
    """
    Generate markdown scorecard from evaluation results.
    """
    scorecard = f"""# Scorecard: {config['label']}

**Timestamp:** {datetime.now().isoformat()}  
**Configuration:** {config_name}  
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

"""
    
    # Add detailed results table
    scorecard += "| # | Query | Answer | F | R | Co | CR |\n"
    scorecard += "|---|-------|--------|---|---|----|----|  \n"
    
    for i, result in enumerate(results, 1):
        query_short = result["query"][:40].replace("\n", " ")
        answer_short = result["answer"][:40].replace("\n", " ") if "answer" in result else "ERROR"
        f = result["scores"]["faithfulness"]
        r = result["scores"]["relevance"]
        co = result["scores"]["completeness"]
        cr = result["scores"]["context_recall"]
        
        scorecard += f"| {i} | {query_short} | {answer_short} | {f} | {r} | {co} | {cr} |\n"
    
    scorecard += "\n---\n\n## Legend\n- **F** = Faithfulness\n- **R** = Relevance\n- **Co** = Completeness\n- **CR** = Context Recall\n"
    
    return scorecard


# =============================================================================
# COMPARISON TABLE
# =============================================================================

def generate_comparison(all_results: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Generate comparison table across all configurations.
    """
    comparison = """# Configuration Comparison

**Date:** """ + datetime.now().isoformat() + """

---

## Summary Statistics

| Configuration | Faithfulness | Relevance | Completeness | Context Recall | Overall Avg |
|---------------|--------------|-----------|--------------|-----------------|------------|
"""
    
    for config_name, results in all_results.items():
        if not results:
            continue
        
        faith_avg = sum(r["scores"]["faithfulness"] for r in results) / len(results)
        relev_avg = sum(r["scores"]["relevance"] for r in results) / len(results)
        complete_avg = sum(r["scores"]["completeness"] for r in results) / len(results)
        context_avg = sum(r["scores"]["context_recall"] for r in results) / len(results)
        overall_avg = (faith_avg + relev_avg + complete_avg + context_avg) / 4
        
        config_label = CONFIGS[config_name]["label"]
        comparison += f"| {config_label} | {faith_avg:.2f} | {relev_avg:.2f} | {complete_avg:.2f} | {context_avg:.2f} | {overall_avg:.2f} |\n"
    
    comparison += """
---

## Delta Analysis (Improvement over Baseline)

"""
    
    if "baseline_dense" in all_results:
        baseline = all_results["baseline_dense"]
        
        for config_name, results in all_results.items():
            if config_name == "baseline_dense":
                continue
            
            if not results:
                continue
            
            baseline_metrics = {
                "faithfulness": sum(r["scores"]["faithfulness"] for r in baseline) / len(baseline),
                "relevance": sum(r["scores"]["relevance"] for r in baseline) / len(baseline),
                "completeness": sum(r["scores"]["completeness"] for r in baseline) / len(baseline),
                "context_recall": sum(r["scores"]["context_recall"] for r in baseline) / len(baseline),
            }
            
            variant_metrics = {
                "faithfulness": sum(r["scores"]["faithfulness"] for r in results) / len(results),
                "relevance": sum(r["scores"]["relevance"] for r in results) / len(results),
                "completeness": sum(r["scores"]["completeness"] for r in results) / len(results),
                "context_recall": sum(r["scores"]["context_recall"] for r in results) / len(results),
            }
            
            config_label = CONFIGS[config_name]["label"]
            comparison += f"\n### {config_label}\n\n"
            comparison += "| Metric | Baseline | Variant | Delta |\n"
            comparison += "|--------|----------|---------|-------|\n"
            
            for metric in ["faithfulness", "relevance", "completeness", "context_recall"]:
                baseline_val = baseline_metrics[metric]
                variant_val = variant_metrics[metric]
                delta = variant_val - baseline_val
                delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
                comparison += f"| {metric} | {baseline_val:.2f} | {variant_val:.2f} | {delta_str} |\n"
    
    return comparison


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RAG PIPELINE EVALUATION — Sprint 3 & 4")
    print("=" * 70)
    
    all_results = {}
    
    # Run evaluation for each config
    for config_name, config in CONFIGS.items():
        print(f"\n[{config_name}] Running evaluation...")
        results = run_evaluation(config, verbose=True)
        all_results[config_name] = results
        
        # Save raw results
        results_file = RESULTS_DIR / f"raw_{config_name}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {results_file}")
        
        # Generate scorecard
        scorecard = generate_scorecard(results, config_name, config)
        scorecard_file = RESULTS_DIR / f"scorecard_{config_name}.md"
        with open(scorecard_file, "w", encoding="utf-8") as f:
            f.write(scorecard)
        print(f"✅ Scorecard saved to {scorecard_file}")
    
    # Generate comparison
    comparison = generate_comparison(all_results)
    comparison_file = RESULTS_DIR / "comparison.md"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison)
    print(f"\n✅ Comparison saved to {comparison_file}")
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to: {RESULTS_DIR}/")
    print("  - scorecard_baseline_dense.md")
    print("  - scorecard_variant_hybrid.md")
    print("  - scorecard_variant_rerank.md")
    print("  - comparison.md")
