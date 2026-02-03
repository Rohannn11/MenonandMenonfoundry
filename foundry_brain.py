import os
import warnings
# Silence TensorFlow/OneDNN noise
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- NEW IMPORTS (Modern Agent Architecture) ---
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

# Import our custom tools
from api_connectors import get_market_data, get_news, get_weather

load_dotenv()

class FoundryBrain:
    def __init__(self):
        # 1. CORE INTELLIGENCE (Groq Llama 3.3)
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY")
        )

        # 2. INTERNAL DATABASE TOOL
        db_uri = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        self.db = SQLDatabase.from_uri(db_uri)
        
        # Sub-agent for SQL (Handles schema complexity)
        self.sql_agent_executor = create_sql_agent(
            llm=self.llm,
            db=self.db,
            agent_type="tool-calling",
            verbose=False
        )

        # 3. KNOWLEDGE BASE TOOL
        emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        if os.path.exists("./chroma_db"):
            self.vector_db = Chroma(persist_directory="./chroma_db", embedding_function=emb, collection_name="foundry_knowledge")
        else:
            self.vector_db = None

        # 4. DEFINE TOOLS
        self.tools = [
            Tool(
                name="Internal_Database",
                func=self.run_sql_query,
                description="Use this for specific factory data: inventory counts, production orders, scrap levels. Input: The full user question."
            ),
            Tool(
                name="Knowledge_Base",
                func=self.query_vectors,
                description="Use this for SOPs, safety rules, defect fixes. Input: The search keyword."
            ),
            Tool(
                name="Market_Data",
                func=get_market_data,
                description="Use this for stock prices, commodities (Steel/Copper), or currency. Input: Ticker symbol (e.g. 'HRC=F') or name."
            ),
            Tool(
                name="News_Search",
                func=get_news,
                description="Use this to find news on ANY topic. Input: Topic string."
            ),
            Tool(
                name="Weather_Check",
                func=get_weather,
                description="Use this for weather. Input: City name."
            )
        ]

        # 5. INITIALIZE AGENT (The Modern Way)
        # We define a prompt that teaches the agent how to use tools
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the Foundry Omni-Agent. You have access to SQL, Market Data, News, and SOPs. "
                       "Use the correct tool to answer the user's question accurately. "
                       "If the user asks for multiple things (e.g. 'Compare internal scrap with steel price'), use multiple tools."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        # Construct the agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        # Create the executor (Runtime)
        self.agent_executor = AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=True, 
            handle_parsing_errors=True
        )

    def run_sql_query(self, query):
        """Wrapper for SQL Agent"""
        try:
            return self.sql_agent_executor.invoke(query)['output']
        except Exception as e:
            return f"SQL Error: {e}"

    def query_vectors(self, query):
        """Wrapper for Vector DB"""
        if not self.vector_db: return "Knowledge Base unavailable."
        docs = self.vector_db.similarity_search(query, k=3)
        return "\n".join([d.page_content for d in docs])

    def ask(self, user_query):
        """
        Main Entry Point
        """
        try:
            # Run the agent
            response = self.agent_executor.invoke({"input": user_query})
            answer = response.get('output', "Task completed.")
            
            return answer, "Omni-Agent", "DYNAMIC"
            
        except Exception as e:
            return f"Agent Error: {str(e)}", "System", "ERROR"