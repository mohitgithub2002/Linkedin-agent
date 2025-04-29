from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging

logger = logging.getLogger(__name__)

class CTAResult(BaseModel):
    cta_text: str = Field(description="The generated call-to-action text")
    action_type: str = Field(description="The type of action being requested")
    urgency_level: str = Field(description="The level of urgency in the CTA")

class CTAGeneratorAgent(BaseAgent):
    """Agent responsible for generating compelling calls-to-action for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("cta_generator")
        self.parser = JsonOutputParser(pydantic_object=CTAResult)
        
    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a professional LinkedIn content creator. Your task is to:
            1. Create an engaging call-to-action (CTA) for a LinkedIn post
            2. Ensure the CTA aligns with the post's content and tone
            3. Make the CTA clear, actionable, and compelling
            
            Consider:
            - The post's main topic and content
            - The target audience
            - The desired action
            - The tone of the post
            
            Format your response as a JSON object with the following structure:
            {{
                "cta_text": "The call-to-action text",
                "action_type": "The type of action (e.g., 'comment', 'share', 'connect')",
                "urgency_level": "The level of urgency (e.g., 'high', 'medium', 'low')"
            }}"""),
            ("human", "Generate a CTA for a post about: {topic}\nContent: {content}")
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"CTA Generator - Input State Type: {type(state)}")
        logger.debug(f"CTA Generator - Input State Content: {state}")
        
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
            raise ValueError("No topic selected for CTA generation")
            
        if not state.body_text:
            logger.error("No body content found in state")
            raise ValueError("No body content available for CTA generation")
            
        prompt = self.create_prompt()
        chain = prompt | self.llm | self.parser
        
        # Get CTA text
        result = await chain.ainvoke({
            "topic": state.current_topic,
            "content": state.body_text
        })
        logger.debug(f"CTA Generation Result: {result}")
        
        # Convert result to CTAResult if it's a dictionary
        if isinstance(result, dict):
            result = CTAResult(**result)
        
        # Update state
        state.cta_text = result.cta_text
        state.messages.append({
            "role": "assistant",
            "content": f"Generated CTA: {result.cta_text}\nAction Type: {result.action_type}\nUrgency Level: {result.urgency_level}"
        })
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
        logger.debug(f"CTA Generator - Output State Type: {type(state)}")
        logger.debug(f"CTA Generator - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_cta", self.run)
        workflow.set_entry_point("generate_cta")
        workflow.add_edge("generate_cta", "end")
        return workflow.compile() 