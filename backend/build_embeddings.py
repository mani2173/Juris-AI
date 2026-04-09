import pandas as pd
from nlp_utils import clean_text
from embeddings import get_embedding

print("📂 Loading dataset...")
df = pd.read_csv("data/final_judge_database.csv")

df = df[['case title', 'issues', 'decision', 'cited cases']]
df.columns = ['case_title', 'issues', 'decision', 'cited_cases']

print("🧹 Cleaning text...")
df['issues'] = df['issues'].fillna("").apply(clean_text)
df['decision'] = df['decision'].fillna("").apply(clean_text)

# 🔥 NEW: Combine for better meaning
df['combined_text'] = df['issues'] + " " + df['decision']

print("🧠 Generating combined embeddings (this will take time)...")
df['combined_embedding'] = df['combined_text'].apply(get_embedding)

print("💾 Saving embeddings to pickle...")
df.to_pickle("data/cases_with_embeddings.pkl")

print("✅ Done! Embeddings saved.")
