from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolNode
import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AgentState(BaseModel):
    """State model for agent workflow."""
    current_topic: Optional[str] = Field(default=None, description="Current topic being processed")
    hook_text: Optional[str] = Field(default=None, description="Generated hook text")
    body_text: Optional[str] = Field(default=None, description="Generated body text")
    cta_text: Optional[str] = Field(default=None, description="Generated call-to-action text")
    research_data: List[Dict[str, str]] = Field(default_factory=list, description="Research data collected")
    messages: List[Dict[str, str]] = Field(default_factory=list, description="Chat messages")
    qa_feedback: Optional[str] = Field(default=None, description="QA feedback on the post")
    qa_suggestions: List[str] = Field(default_factory=list, description="QA suggestions for improvement")
    qa_score: Optional[int] = Field(default=None, description="QA score from 1-10")
    qa_issues: List[str] = Field(default_factory=list, description="QA identified issues")
    post_payload: Optional[Dict[str, Any]] = Field(default=None, description="Final assembled post payload")
    image_url: Optional[str] = Field(default=None, description="URL for post image")

class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, tools: Optional[List[BaseTool]] = None):
        self.name = name
        self.tools = tools or []
        self.tool_node = ToolNode(self.tools) if self.tools else None
        
        # Initialize LLM with default configuration
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=api_key,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        )
        
        logger.info(f"Initialized {self.name} agent with {len(self.tools)} tools and LLM configured")
        
    def set_llm(self, llm: BaseChatModel):
        """Set the language model for the agent."""
        if not isinstance(llm, BaseChatModel):
            raise ValueError("LLM must be an instance of BaseChatModel")
        self.llm = llm
        logger.debug(f"Set custom LLM for {self.name} agent")
        
    def add_tool(self, tool: BaseTool):
        """Add a tool to the agent's toolkit."""
        if not isinstance(tool, BaseTool):
            raise ValueError("Tool must be an instance of BaseTool")
        self.tools.append(tool)
        self.tool_node = ToolNode(self.tools)
        logger.debug(f"Added tool {tool.name} to {self.name} agent")
        
    def create_chain(self, prompt: ChatPromptTemplate) -> Any:
        """Create a chain with the LLM and parser."""
        if not self.llm:
            raise ValueError("LLM not initialized. Call set_llm() first.")
        return prompt | self.llm
        
    async def run(self, state: AgentState) -> AgentState:
        """Run the agent's main logic."""
        raise NotImplementedError("Subclasses must implement run method")
        
    def create_prompt(self, system_prompt: str) -> ChatPromptTemplate:
        """Create a chat prompt template for the agent."""
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        
    def get_graph(self) -> Graph:
        """Get the agent's workflow graph."""
        raise NotImplementedError("Subclasses must implement get_graph method") 