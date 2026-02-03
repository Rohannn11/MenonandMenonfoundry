import os
import shutil
import hashlib
import argparse
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings # <--- NEW LOCAL EMBEDDINGS
from langchain_chroma import Chroma
from langchain_core.documents import Document
from api_connectors import get_foundry_news

load_dotenv()

CHROMA_PATH = "./chroma_db"
# This model downloads once (approx 80MB) and runs locally. fast & free.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

SOP_TEXTS = [
    # MELTING
    "Melting SOP: Start induction furnace with 20% heel. Add carburizer first, then steel scrap.",
    "Melting Safety: Verify lining thickness before every heat. Refractory thickness < 50mm is CRITICAL FAIL.",
    "Melting Temp: Grey Iron tap temp 1420C-1450C. SG Iron tap temp 1480C-1520C.",
    "Melting Defect: Low carbon (<3.0%) causes shrinkage. High silicon (>2.5%) causes ferritic structure.",
    # MOLDING
    "Molding SOP: Sand moisture must be 3.0-3.6%. GCS > 1200 gm/cm2.",
    "Molding Defect: 'Blowholes' caused by high moisture or low permeability. Fix: Increase venting.",
    "Molding Defect: 'Sand Drop' caused by low compactability. Fix: Increase clay/water ratio.",
    # CASTING
    "Casting SOP: Pouring time should not exceed (Weight_kg * 1.5) seconds.",
    "Casting Safety: Ladle preheating to 800C mandatory to prevent hydrogen pickup.",
    "Casting Defect: 'Misrun' caused by low temp. Fix: Increase tap temp by 20C.",
    # QUALITY
    "Quality Standard: Tensile Strength Class 25 = 250 MPa min. Brinell Hardness 180-220 HB.",
    "Inventory Rule: Scrap Steel safety stock = 5000 kg. Reorder point = 7000 kg."
]

def get_doc_id(content):
    return hashlib.md5(content.encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--news", action="store_true", help="Update only news")
    args = parser.parse_args()

    print("--- 🧠 INITIALIZING LOCAL EMBEDDINGS (HuggingFace) ---")
    # This runs locally. No API limits.
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    if not args.news:
        if os.path.exists(CHROMA_PATH):
            shutil.rmtree(CHROMA_PATH)
            print("    Cleared old database.")

    vector_db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
        collection_name="foundry_knowledge"
    )

    if not args.news:
        print(f"    Ingesting {len(SOP_TEXTS)} SOPs...")
        docs = [Document(page_content=t, metadata={"source": "SOP", "type": "static"}) for t in SOP_TEXTS]
        vector_db.add_documents(docs, ids=[get_doc_id(d.page_content) for d in docs])

    print("    Fetching Live News...")
    news_items = get_foundry_news()
    if news_items and "Error" not in news_items[0]:
        docs = [Document(page_content=t, metadata={"source": "NewsAPI", "type": "dynamic"}) for t in news_items]
        vector_db.add_documents(docs, ids=[get_doc_id(d.page_content) for d in docs])
        print(f"    Added {len(docs)} news articles.")

    print(f"✅ SUCCESS: Knowledge Base ready at {CHROMA_PATH}")

if __name__ == "__main__":
    main()