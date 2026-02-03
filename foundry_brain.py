import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_chroma import Chroma
from api_connectors import get_metal_prices, get_pune_weather, get_foundry_news, format_for_llm
import warnings
import logging

# --- 1. SILENCE WARNINGS (Must be before other imports) ---
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"      # Turns off OneDNN custom operations info
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"      # 3 = FATAL only (hides INFO and WARNING)
warnings.filterwarnings("ignore")              # Hides Python FutureWarnings/Deprecations
logging.getLogger("transformers").setLevel(logging.ERROR) # Hides HuggingFace noise

# --- 2. STANDARD IMPORTS ---
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_chroma import Chroma
from api_connectors import get_metal_prices, get_pune_weather, get_foundry_news, format_for_llm
load_dotenv()

class FoundryBrain:
    def __init__(self):
        # 1. SETUP GROQ (Updated Model Name)
        # using Llama 3.3 70B (Current Stable)
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile", 
            temperature=0,
            max_retries=2,
            api_key=os.getenv("GROQ_API_KEY")
        )

        # 2. LOAD SCHEMA
        try:
            with open("schema.sql", "r") as f:
                self.schema_context = f.read()
        except:
            self.schema_context = "Error loading schema.sql"

        # 3. CONNECT DB
        db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        self.db = SQLDatabase.from_uri(db_uri)

        # 4. CONNECT VECTORS (Local HF Embeddings)
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        if os.path.exists("./chroma_db"):
            self.vector_db = Chroma(persist_directory="./chroma_db", embedding_function=emb, collection_name="foundry_knowledge")
        else:
            self.vector_db = None

    def _router(self, query):
        """Simple keyword router to save API calls."""
        q = query.lower()
        if any(x in q for x in ['count', 'total', 'how many', 'inventory', 'stock', 'order', 'status', 'production', 'scrap', 'maintenance']):
            return 'DATABASE'
        if any(x in q for x in ['price', 'market', 'rate', 'weather', 'news', 'usd', 'cost']):
            return 'EXTERNAL'
        return 'KNOWLEDGE'

    def ask(self, query):
        start_time = time.time()
        intent = self._router(query)
        context = ""
        source_label = ""

        try:
            # --- PATH 1: SQL DATABASE ---
            if intent == 'DATABASE':
                source_label = "SQL Database"
                # Step A: Generate SQL
                system_msg = f"""You are a PostgreSQL expert. Given the schema, write a valid SQL query to answer the user.
                
                SCHEMA:
                {self.schema_context}
                
                RULES:
                1. Return ONLY the SQL. No markdown (```), no explanations.
                2. Use ILIKE for text searches.
                3. If specific ID is unknown, use LIMIT 5.
                
                User: {query}"""
                
                sql_query = self.llm.invoke(system_msg).content.strip().replace("```sql", "").replace("```", "")
                
                # Step B: Execute
                try:
                    res = self.db.run(sql_query)
                    context = f"SQL: {sql_query}\nDATA: {res}"
                except Exception as e:
                    context = f"SQL Error: {e}"

            # --- PATH 2: EXTERNAL API ---
            elif intent == 'EXTERNAL':
                source_label = "Live API"
                data = []
                q_low = query.lower()
                if "weather" in q_low: data.append(format_for_llm(get_pune_weather(), "WEATHER"))
                if "news" in q_low: data.append(format_for_llm(get_foundry_news(), "NEWS"))
                if any(x in q_low for x in ["price", "rate", "cost", "market"]): 
                    data.append(format_for_llm(get_metal_prices(), "MARKETS"))
                
                context = "\n".join(data)

            # --- PATH 3: KNOWLEDGE ---
            else:
                source_label = "Knowledge Base"
                if self.vector_db:
                    docs = self.vector_db.similarity_search(query, k=3)
                    context = "\n".join([f"- {d.page_content}" for d in docs])
                else:
                    context = "No Knowledge Base found."

            # --- FINAL ANSWER ---
            final_prompt = f"""
            You are 'Foundry Sahayak'. Answer the user using the provided context.
            
            CONTEXT ({source_label}):
            {context}
            
            USER QUERY: {query}
            
            GUIDELINES:
            1. Be professional and concise.
            2. If the context contains data, explicitly mention the numbers.
            3. If context is empty, admit you don't know.
            """
            
            response = self.llm.invoke(final_prompt).content
            elapsed = round(time.time() - start_time, 2)
            
            return response + f"\n\n_⚡ {elapsed}s | Powered by Groq_", source_label, intent

        except Exception as e:
            return f"System Error: {str(e)}", "ERROR", "ERROR"