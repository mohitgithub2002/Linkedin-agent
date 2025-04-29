from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain.tools import Tool
from langgraph.graph import Graph, StateGraph
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class ResearchItem(BaseModel):
    source: str = Field(description="The source of the information")
    snippet: str = Field(description="The relevant information from the source")

class ResearchResult(BaseModel):
    items: List[ResearchItem] = Field(description="List of research items found")

class ResearchAgent(BaseAgent):
    """Agent responsible for gathering research and supporting content."""
    
    def __init__(self):
        tools = [
            Tool(
                name="web_search",
                func=self._web_search,
                description="Search the web for relevant information"
            )
        ]
        super().__init__("research_agent", tools)
        self.parser = JsonOutputParser(pydantic_object=ResearchResult)
        
    def _web_search(self, query: str) -> str:
        """Perform a web search and extract relevant information."""
        # This is a simplified version. In production, you'd want to use a proper search API
        try:
            response = requests.get(f"https://www.google.com/search?q={query}")
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', class_='g')
            return "\n".join([result.get_text() for result in results[:3]])
        except Exception as e:
            return f"Error performing web search: {str(e)}"
    
    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant for LinkedIn content creation. Your task is to:
            1. Gather relevant facts, statistics, and supporting information
            2. Verify the credibility of sources
            3. Extract key insights that support the main topic
            
            Format your findings as a JSON object with the following structure:
            {{
                "items": [
                    {{
                        "source": "The source of the information",
                        "snippet": "The relevant information from the source"
                    }}
                ]
            }}"""),
            ("human", "Research information about: {topic}")
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"Research Agent - Input State Type: {type(state)}")
        logger.debug(f"Research Agent - Input State Content: {state}")
        
        # Convert state dictionary to AgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to AgentState")
            state = AgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        # Save initial checkpoint
        self.save_checkpoint(state)
            
        if not state.current_topic:
            logger.error("No topic found in state")
            raise ValueError("No topic selected for research")
            
        prompt = self.create_prompt()
        chain = prompt | self.llm | self.parser
        
        # Get research data
        result = await chain.ainvoke({"topic": state.current_topic})
        logger.debug(f"Research Result: {result}")
        
        # Convert result to ResearchResult if it's a dictionary
        if isinstance(result, dict):
            result = ResearchResult(**result)
        
        # Update state with all research items
        for item in result.items:
            state.research_data.append({
                "source": item.source,
                "snippet": item.snippet
            })
        
        state.messages.append({
            "role": "assistant",
            "content": f"Research completed for topic: {state.current_topic}. Found {len(result.items)} items."
        })
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
        logger.debug(f"Research Agent - Output State Type: {type(state)}")
        logger.debug(f"Research Agent - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("research", self.run)
        workflow.set_entry_point("research")
        workflow.add_edge("research", "end")
        return workflow.compile() 