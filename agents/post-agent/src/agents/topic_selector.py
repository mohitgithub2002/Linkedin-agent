from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging

logger = logging.getLogger(__name__)

class KeyPoint(BaseModel):
    heading: str = Field(description="The heading for this key point")
    content: str = Field(description="The content for this key point")
    optional_visual: str | None = Field(default=None, description="Optional visual suggestion")
    call_to_action: str | None = Field(default=None, description="Optional call to action")

class Brief(BaseModel):
    title: str = Field(description="The title of the post")
    target_audience: str = Field(description="The target audience for the post")
    key_points: List[KeyPoint] = Field(description="List of key points to cover")
    tone: str = Field(description="The tone to use in the post")
    hashtags: List[str] = Field(description="Relevant hashtags for the post")

class TopicBrief(BaseModel):
    current_topic: str = Field(description="The selected topic for the LinkedIn post")
    brief: Brief = Field(description="A structured brief for the post")

class TopicSelectorAgent(BaseAgent):
    """Agent responsible for selecting topics for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("topic_selector")
        self.parser = JsonOutputParser(pydantic_object=TopicBrief)
        
    def create_prompt(self, with_topic: bool = False) -> ChatPromptTemplate:
        if with_topic:
            system_message = """You are a professional LinkedIn content strategist. Your task is to:
            1. Create a detailed brief for a LinkedIn post on the given topic
            2. Identify the target audience
            3. Outline key points to cover
            4. Suggest an appropriate tone
            5. Recommend relevant hashtags
            
            Format your response as a JSON object with the following structure:
            {{
                "current_topic": "{topic}",
                "brief": {{
                    "title": "The title of the post",
                    "target_audience": "Who this post is for",
                    "key_points": [
                        {{
                            "heading": "Key point heading",
                            "content": "Detailed content for this point",
                            "optional_visual": "Optional visual suggestion",
                            "call_to_action": "Optional call to action"
                        }}
                    ],
                    "tone": "The tone to use in the post",
                    "hashtags": ["#relevant", "#hashtags"]
                }}
            }}"""
            human_message = "Create a detailed brief for a LinkedIn post on: {topic}"
        else:
            system_message = """You are a professional LinkedIn content strategist. Your task is to:
            1. Select an engaging topic for a LinkedIn post
            2. Create a detailed brief for the post
            3. Identify the target audience
            4. Outline key points to cover
            5. Suggest an appropriate tone
            6. Recommend relevant hashtags
            
            Format your response as a JSON object with the following structure:
            {{
                "current_topic": "The main topic of the post",
                "brief": {{
                    "title": "The title of the post",
                    "target_audience": "Who this post is for",
                    "key_points": [
                        {{
                            "heading": "Key point heading",
                            "content": "Detailed content for this point",
                            "optional_visual": "Optional visual suggestion",
                            "call_to_action": "Optional call to action"
                        }}
                    ],
                    "tone": "The tone to use in the post",
                    "hashtags": ["#relevant", "#hashtags"]
                }}
            }}"""
            human_message = "{input}"
            
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"Topic Selector - Input State Type: {type(state)}")
        logger.debug(f"Topic Selector - Input State Content: {state}")
        
        # Convert state dictionary to AgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to AgentState")
            state = AgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        # Check if a topic is already provided
        if state.current_topic:
            logger.info(f"Using provided topic: {state.current_topic}")
            prompt = self.create_prompt(with_topic=True)
            chain = prompt | self.llm | self.parser
            
            # Create a brief for the provided topic
            result = await chain.ainvoke({"topic": state.current_topic})
            logger.debug(f"Topic Brief Result: {result}")
        else:
            logger.info("No topic provided, selecting a new topic")
            prompt = self.create_prompt(with_topic=False)
            chain = prompt | self.llm | self.parser
            
            # Select a new topic and create a brief
            result = await chain.ainvoke({"input": "Select a topic for a LinkedIn post"})
            logger.debug(f"Topic Selection Result: {result}")
        
        # Convert result to TopicBrief if it's a dictionary
        if isinstance(result, dict):
            result = TopicBrief(**result)
        
        # Update state
        state.current_topic = result.current_topic
        state.messages.append({
            "role": "assistant",
            "content": f"Selected topic: {result.current_topic}\nBrief: {result.brief.model_dump_json()}"
        })
        
        logger.debug(f"Topic Selector - Output State Type: {type(state)}")
        logger.debug(f"Topic Selector - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("select_topic", self.run)
        workflow.set_entry_point("select_topic")
        workflow.add_edge("select_topic", "end")
        return workflow.compile() 