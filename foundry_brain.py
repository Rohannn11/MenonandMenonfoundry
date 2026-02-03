import os
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from api_connectors import get_metal_prices, get_foundry_news

load_dotenv()

# 1. SETUP DATABASE & VECTOR STORE
db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
db = SQLDatabase.from_uri(db_uri)

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
vector_path = "./chroma_db"
vector_db = Chroma(persist_directory=vector_path, embedding_function=embeddings) if os.path.exists(vector_path) else None

# 2. DEFINE LIGHTWEIGHT TOOLS (Token Efficient)

@tool
def ask_database(query: str) -> str:
    """
    Use this to query the SQL database for counts, inventory, orders, or records.
    Input should be a valid SQL query.
    Schema hints:
    - material_master (Material_Number, Material_Type)
    - inventory_movements (Quantity, Movement_Type)
    - production_orders (Order_Status, Product_Type)
    - melting_heat_records (Heat_Number, Tap_Temperature_C)
    """
    try:
        return db.run(query)
    except Exception as e:
        return f"SQL Error: {e}"

@tool
def ask_knowledge_base(query: str) -> str:
    """
    Use this for 'How-to', SOPs, safety rules, or defects.
    Searches the vector database.
    """
    if not vector_db: return "Knowledge Base not loaded."
    results = vector_db.similarity_search(query, k=2)
    return "\n".join([d.page_content for d in results])

@tool
def check_market_data(query: str) -> str:
    """
    Use this for real-time prices (Copper, Steel, Oil) or News.
    """
    if "news" in query.lower():
        return get_foundry_news()
    return get_metal_prices()

# 3. THE BRAIN CLASS

class FoundryBrain:
    def __init__(self):
        # We use 1.5-flash because it is the designated free-tier model.
        # 2.0-flash often gates free users quickly (Error 429).
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            temperature=0,
            max_retries=3
        )
        
        self.tools = [ask_database, ask_knowledge_base, check_market_data]
        
        # New "Tool Calling" Prompt (More robust than ReAct)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Foundry Sahayak. You have access to SQL, Knowledge Base, and Market Data. Use the correct tool to answer."),
            ("user", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    def ask(self, user_input: str):
        try:
            # Fallback check to avoid API calls for empty queries
            if not user_input.strip(): return "Please ask a question.", "None"
            
            response = self.executor.invoke({"input": user_input})
            return response['output'], "Agent"
            
        except Exception as e:
            # Graceful Error Handling (No more stack traces in UI)
            if "429" in str(e):
                return "⚠️ Traffic High (Quota). Showing Cached/Fallback info if available.", "System"
            return f"I encountered an error: {str(e)}", "System Error"