from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_embeddings(contents):
    return model.encode(contents, show_progress_bar=False)