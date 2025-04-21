from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging

logger = logging.getLogger(__name__)

class PostPayload(BaseModel):
    text: str = Field(description="The complete LinkedIn post text")
    image_url: str = Field(description="URL of the post image")

class FinalAssemblerAgent(BaseAgent):
    """Agent responsible for assembling the final LinkedIn post."""
    
    def __init__(self):
        super().__init__("final_assembler")
        self.parser = JsonOutputParser(pydantic_object=PostPayload)
        
    def create_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", """You are a professional LinkedIn content editor. Your task is to:
            1. Combine the hook, body, and CTA into a cohesive post
            2. Ensure proper formatting and spacing
            3. Add relevant hashtags
            4. Optimize for LinkedIn's algorithm
            
            Guidelines:
            - Maintain a professional tone
            - Use proper paragraph breaks
            - Include relevant hashtags
            - Keep the post within LinkedIn's character limit
            - Ensure smooth transitions between sections
            
            Format your response as a JSON object with the following structure:
            {{
                "text": "The complete LinkedIn post text",
                "image_url": "URL of the post image or leave empty string if none"
            }}"""),
            ("human", "Assemble the final LinkedIn post with:\nTopic: {topic}\nHook: {hook}\nBody: {body}\nCTA: {cta}")
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"Final Assembler - Input State Type: {type(state)}")
        logger.debug(f"Final Assembler - Input State Content: {state}")
        
        # Convert state dictionary to AgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to AgentState")
            state = AgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        if not state.current_topic:
            logger.error("No topic found in state")
            raise ValueError("No topic selected for post assembly")
            
        if not state.hook_text:
            logger.error("No hook found in state")
            raise ValueError("No hook generated for post assembly")
            
        if not state.body_text:
            logger.error("No body content found in state")
            raise ValueError("No body content available for post assembly")
            
        if not state.cta_text:
            logger.error("No CTA found in state")
            raise ValueError("No CTA available for post assembly")
            
        prompt = self.create_prompt()
        chain = prompt | self.llm | self.parser
        
        # Get final post payload
        result = await chain.ainvoke({
            "topic": state.current_topic,
            "hook": state.hook_text,
            "body": state.body_text,
            "cta": state.cta_text
        })
        logger.debug(f"Post Assembly Result: {result}")
        
        # Convert result to PostPayload if it's a dictionary
        if isinstance(result, dict):
            result = PostPayload(**result)
        
        # Update state
        state.post_payload = {
            "text": result.text,
            "image_url": result.image_url or ""
        }
        state.messages.append({
            "role": "assistant",
            "content": f"Final post assembled successfully:\n{result.text}"
        })
        
        logger.debug(f"Final Assembler - Output State Type: {type(state)}")
        logger.debug(f"Final Assembler - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("assemble_post", self.run)
        workflow.set_entry_point("assemble_post")
        workflow.add_edge("assemble_post", "end")
        return workflow.compile() 