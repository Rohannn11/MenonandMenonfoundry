import os
from dotenv import load_dotenv

# --- 1. NATIVE IMPORTS (No Adapters) ---
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

# Import Tools
from core.tools import get_market_data, get_global_news, query_internal_sops

load_dotenv()

class AgentBrain:
    def __init__(self):
        # 2. SETUP LLM (Using Native Groq Class)
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            api_key=os.getenv("GROQ_API_KEY")
        )

        # 3. DEFINE TOOLS
        self.tools = [
            get_market_data,
            get_global_news,
            query_internal_sops
        ]

        # 4. DEFINE PERSONA
        self.system_prompt = (
            "You are the Foundry AI. "
            "Use 'get_market_data' for prices. "
            "Use 'query_internal_sops' for factory rules. "
            "Use 'get_global_news' for trends. "
            "Be professional and concise."
        )

        # 5. BUILD THE GRAPH
        # This creates the executable agent using the Native Groq LLM
        self.agent = create_react_agent(self.llm, self.tools)

    def ask(self, query):
        try:
            # 6. EXECUTE
            messages = [
                ("system", self.system_prompt),
                ("user", query)
            ]
            
            response = self.agent.invoke(
                {"messages": messages},
                {"recursion_limit": 10}
            )
            
            # 7. EXTRACT ANSWER
            return response["messages"][-1].content
            
        except Exception as e:
            return f"System Error: {str(e)}"