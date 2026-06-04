from benchmark.rag_recall import RetrievalCase, evaluate_recall, recall_at_k


def test_recall_at_k_hits_partial_targets():
    score = recall_at_k([101, 102], [101, 999, 888], 5)
    assert score == 0.5


def test_recall_at_k_ignores_results_beyond_k():
    score = recall_at_k([2], [10, 11, 12, 13, 2], 4)
    assert score == 0.0


def test_evaluate_recall_returns_mean_scores():
    report = evaluate_recall(
        [
            RetrievalCase(query="函数", expected_source_ids=[1], retrieved_source_ids=[1, 2, 3]),
            RetrievalCase(query="力学", expected_source_ids=[10, 11], retrieved_source_ids=[11, 50, 10]),
        ]
    )
    assert report["Recall@5"] == 1.0
    assert report["Recall@10"] == 1.0
