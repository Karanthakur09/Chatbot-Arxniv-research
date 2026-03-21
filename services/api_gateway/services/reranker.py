from sentence_transformers import CrossEncoder

# production-grade reranker
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query, results, top_k=5):

    pairs = [(query, r["content"]) for r in results]

    scores = model.predict(pairs)

    for r, score in zip(results, scores):
        r["rerank_score"] = float(score)

    results.sort(key=lambda x: x["rerank_score"], reverse=True)

    return results[:top_k]