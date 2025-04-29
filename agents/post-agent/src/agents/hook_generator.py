from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging

logger = logging.getLogger(__name__)

class HookResult(BaseModel):
    hook_text: str = Field(description="The generated hook text for the LinkedIn post")
    tone: str = Field(description="The tone used in the hook")
    target_audience: str = Field(description="The target audience for the hook")

class HookGeneratorAgent(BaseAgent):
    """Agent responsible for generating engaging hooks for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("hook_generator")
        self.parser = JsonOutputParser(pydantic_object=HookResult)
        
    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a professional LinkedIn content creator. Your task is to:
            1. Create an engaging hook for a LinkedIn post
            2. Ensure the hook captures attention and encourages reading
            3. Match the tone and target audience of the post
            
            Consider:
            - The main topic
            - The target audience
            - Current trends
            - Professional tone
            
            Format your response as a JSON object with the following structure:
            {{
                "hook_text": "The engaging hook text",
                "tone": "The tone used in the hook",
                "target_audience": "The target audience for the hook"
            }}"""),
            ("human", "Generate a hook for a post about: {topic}")
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"Hook Generator - Input State Type: {type(state)}")
        logger.debug(f"Hook Generator - Input State Content: {state}")
        
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
            raise ValueError("No topic selected for hook generation")
            
        prompt = self.create_prompt()
        chain = prompt | self.llm | self.parser
        
        # Get hook text
        result = await chain.ainvoke({"topic": state.current_topic})
        logger.debug(f"Hook Generation Result: {result}")
        
        # Convert result to HookResult if it's a dictionary
        if isinstance(result, dict):
            result = HookResult(**result)
        
        # Update state
        state.hook_text = result.hook_text
        state.messages.append({
            "role": "assistant",
            "content": f"Generated hook: {result.hook_text}\nTone: {result.tone}\nTarget Audience: {result.target_audience}"
        })
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
        logger.debug(f"Hook Generator - Output State Type: {type(state)}")
        logger.debug(f"Hook Generator - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_hook", self.run)
        workflow.set_entry_point("generate_hook")
        workflow.add_edge("generate_hook", "end")
        return workflow.compile() 