from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_query(query: str):
    return model.encode(query).tolist()

from shared.cache import get_cache, set_cache

def embed_query_cached(query: str):

    cache_key = f"embed:{query}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    vector = embed_query(query)

    set_cache(cache_key, vector, ttl=3600)  # 1 hour

    return vector