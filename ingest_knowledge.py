import os
import shutil
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from api_connectors import get_foundry_news  # Import the news fetcher

load_dotenv()

CHROMA_PATH = "./chroma_db"
EMBEDDING_MODEL = "models/text-embedding-004"

def ingest():
    print("--- STARTING KNOWLEDGE INGESTION ---")
    
    # 1. Static Foundry SOPs (The Rules)
    sop_texts = [
        "SOP: Sand Moisture must be maintained between 3.0% and 3.5%. Low moisture causes crumbling; high causes blowholes.",
        "Safety: Operators must wear Aluminized Aprons when near the Induction Furnace. Eye protection is mandatory.",
        "Quality Standard: Grade A Castings must have zero porosity visible to naked eye.",
        "Procedure: If Tap Temperature < 1400C, do not pour. Return metal to furnace to prevent cold shuts.",
        "Inventory Policy: Scrap Steel inventory should never drop below 5,000 KG."
    ]
    docs = [Document(page_content=t, metadata={"source": "SOP_Manual", "type": "static"}) for t in sop_texts]
    print(f"Loaded {len(docs)} Static SOPs.")

    # 2. Dynamic Market News (The Context)
    print("Fetching Live News...")
    news_items = get_foundry_news()
    if news_items:
        news_docs = [Document(page_content=t, metadata={"source": "NewsAPI", "type": "news"}) for t in news_items]
        docs.extend(news_docs)
        print(f"Loaded {len(news_docs)} News Articles.")
    else:
        print("No news fetched (check API key).")

    # 3. Rebuild ChromaDB
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH) # Clear old data
        print("Cleared previous database.")

    print("Embedding data (this may take a moment)...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_PATH)
    
    print(f"✅ SUCCESS: Database built at {CHROMA_PATH} with {len(docs)} total records.")

if __name__ == "__main__":
    ingest()