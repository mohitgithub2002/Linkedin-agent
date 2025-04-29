from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging
import re
import json

logger = logging.getLogger(__name__)

class BodyResult(BaseModel):
    body_text: str = Field(description="The generated body text for the LinkedIn post")
    key_points: List[str] = Field(description="List of key points covered in the body")
    tone: str = Field(description="The tone used in the body")

class BodyGeneratorAgent(BaseAgent):
    """Agent responsible for generating the main body content for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("body_generator")
        self.parser = JsonOutputParser(pydantic_object=BodyResult)
        
    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a professional LinkedIn content creator. Your task is to:
            1. Create engaging body content for a LinkedIn post
            2. Ensure the content flows naturally from the hook
            3. Include relevant research and insights
            4. Maintain a professional and engaging tone
            
            Consider:
            - The hook and its tone to ensure smooth transition
            - The topic and its context
            - Research data and insights
            - Target audience
            - Professional value
            
            Format your response as a JSON object with the following structure:
            {{
                "body_text": "The main body content",
                "key_points": ["Key point 1", "Key point 2", ...],
                "tone": "The tone used in the body"
            }}"""),
            ("human", "Generate body content for a post about: {topic}\nHook: {hook}\nResearch Context:\n{research}")
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"Body Generator - Input State Type: {type(state)}")
        logger.debug(f"Body Generator - Input State Content: {state}")
        
        # Convert state dictionary to AgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to AgentState")
            state = AgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        # Save initial checkpoint
        self.save_checkpoint(state)
            
        # Validate input state
        if not state.current_topic:
            raise ValueError("No topic provided in state")
            
        if not state.hook_text:
            raise ValueError("No hook provided in state")
            
        # Create prompt
        prompt = self.create_prompt()
        chain = prompt | self.llm | self.parser
        
        try:
            # Prepare research context
            research_context = "\n".join([
                f"{item['source']}: {item['snippet']}"
                for item in state.research_data
            ]) if state.research_data else "No research data available"
            
            # Invoke the chain
            result = await chain.ainvoke({
                "topic": state.current_topic,
                "hook": state.hook_text,
                "research": research_context
            })
            
            # Handle markdown code blocks in the output
            if isinstance(result, str):
                # Remove markdown code block markers and any leading/trailing whitespace
                result = re.sub(r'```json\n?|\n?```', '', result).strip()
                try:
                    # Parse the cleaned JSON
                    result = json.loads(result)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    logger.error(f"Raw output: {result}")
                    raise ValueError(f"Invalid JSON output: {str(e)}")
            
            # Convert result to BodyResult if it's a dictionary
            if isinstance(result, dict):
                result = BodyResult(**result)
            elif not isinstance(result, BodyResult):
                raise ValueError(f"Unexpected result type: {type(result)}")
            
            # Update state
            state.body_text = result.body_text
            state.messages.append({
                "role": "assistant",
                "content": f"Generated body text: {result.body_text}"
            })
            
            # Save final checkpoint
            self.save_checkpoint(state)
            
        except Exception as e:
            logger.error(f"Error in BodyGeneratorAgent: {str(e)}")
            raise
        
        logger.debug(f"Body Generator - Output State Type: {type(state)}")
        logger.debug(f"Body Generator - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_body", self.run)
        workflow.set_entry_point("generate_body")
        workflow.add_edge("generate_body", "end")
        return workflow.compile() 