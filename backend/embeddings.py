from sentence_transformers import SentenceTransformer

print("🔁 Loading sentence transformer model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("✅ Model loaded!")

def get_embedding(text):
    return model.encode(text).tolist()
