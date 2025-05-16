from typing import Any, Dict, List, Union
from .base import BaseAgent, AgentState
from .identity_agent import IdentityAgentState
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
        
    def create_prompt(self, identity_spec: Any) -> ChatPromptTemplate:
        # Convert complex objects to simple strings to avoid formatting issues
        voice_str = str(identity_spec.voice).replace("{", "{{").replace("}", "}}")
        pillars_str = str(identity_spec.pillars_ranked).replace("{", "{{").replace("}", "}}")
        stories_str = str(identity_spec.signature_stories).replace("{", "{{").replace("}", "}}")
        
        # Create a simple system message with no JSON example
        system_message = f"""You are a professional LinkedIn content creator for {identity_spec.creator}. 

Your task is to create engaging body content for a LinkedIn post that:
1. Aligns with the creator's brand identity
2. Flows naturally from the hook
3. Includes relevant research and insights
4. Maintains the creator's voice and tone: {voice_str}
5. Incorporates the creator's brand pillars: {pillars_str}
6. Supports the creator's promise: {identity_spec.promise}

Consider these elements:
- The hook and its tone to ensure smooth transition
- The topic and its context
- Research data and insights
- Target audience
- Professional value
- Creator's signature stories: {stories_str}

Output a JSON with these fields:
- body_text: The main content as a string
- key_points: A list of key points covered in the body
- tone: A SINGLE word or phrase describing the tone (e.g. "professional" or "conversational"), not a list"""

        # Create a completely separate human message template
        human_message = "Generate body content for a post about: {topic}\nHook: {hook}\nResearch Context:\n{research}"
        
        # Create template with simple parts
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    
    async def run(self, state: IdentityAgentState) -> IdentityAgentState:
        logger.debug(f"Body Generator - Input State Type: {type(state)}")
        logger.debug(f"Body Generator - Input State Content: {state}")
        
        # Convert state dictionary to IdentityAgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to IdentityAgentState")
            state = IdentityAgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        # Save initial checkpoint
        self.save_checkpoint(state)
            
        # Validate input state
        if not state.current_topic:
            raise ValueError("No topic provided in state")
            
        if not state.hook_text:
            raise ValueError("No hook provided in state")
            
        if not state.identity_spec:
            raise ValueError("Identity specification required for body generation")
            
        # Create prompt
        prompt = self.create_prompt(state.identity_spec)
        logger.debug(f"Prompt variables: {prompt.input_variables}")
        chain = prompt | self.llm | self.parser
        
        try:
            # Prepare research context
            research_context = "\n".join([
                f"{item['source']}: {item['snippet']}"
                for item in state.research_data
            ]) if state.research_data else "No research data available"
            
            # Log the inputs
            logger.debug(f"Invoking chain with topic: {state.current_topic}")
            logger.debug(f"Hook: {state.hook_text}")
            logger.debug(f"Research Context (length): {len(research_context)}")
            
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
            
            # Handle case where tone might be a list instead of a string
            if isinstance(result, dict) and "tone" in result and isinstance(result["tone"], list):
                logger.warning(f"Tone returned as a list: {result['tone']}. Converting to string.")
                result["tone"] = ", ".join(result["tone"])
            
            # Convert result to BodyResult if it's a dictionary
            if isinstance(result, dict):
                result = BodyResult(**result)
            elif not isinstance(result, BodyResult):
                raise ValueError(f"Unexpected result type: {type(result)}")
                
            # Validate body against identity rules
            if state.validators and "body" in state.validators:
                is_valid, error_msg = state.validators["body"](result.body_text)
                if not is_valid:
                    logger.warning(f"Body validation failed: {error_msg}")
                    # Retry with more specific guidance
                    prompt = self.create_prompt(state.identity_spec)
                    chain = prompt | self.llm | self.parser
                    retry_result = await chain.ainvoke({
                        "topic": state.current_topic,
                        "hook": state.hook_text,
                        "research": research_context,
                        "error": f"Previous body failed validation: {error_msg}. Please try again."
                    })
                    
                    # Handle case where tone might be a list in retry
                    if isinstance(retry_result, dict) and "tone" in retry_result and isinstance(retry_result["tone"], list):
                        logger.warning(f"Tone returned as a list in retry: {retry_result['tone']}. Converting to string.")
                        retry_result["tone"] = ", ".join(retry_result["tone"])
                        
                    if isinstance(retry_result, dict):
                        result = BodyResult(**retry_result)
                        
            # Score tone if validator available
            if state.validators and "tone" in state.validators:
                tone_score = state.validators["tone"](result.body_text)
                logger.info(f"Body tone score: {tone_score}")
                if tone_score < 0.6:  # Threshold for acceptable tone
                    logger.warning("Body tone score too low, regenerating")
                    prompt = self.create_prompt(state.identity_spec)
                    chain = prompt | self.llm | self.parser
                    retry_result = await chain.ainvoke({
                        "topic": state.current_topic,
                        "hook": state.hook_text,
                        "research": research_context,
                        "error": "Previous body tone score was too low. Please improve readability and engagement."
                    })
                    
                    # Handle case where tone might be a list in retry
                    if isinstance(retry_result, dict) and "tone" in retry_result and isinstance(retry_result["tone"], list):
                        logger.warning(f"Tone returned as a list in tone retry: {retry_result['tone']}. Converting to string.")
                        retry_result["tone"] = ", ".join(retry_result["tone"])
                        
                    if isinstance(retry_result, dict):
                        result = BodyResult(**retry_result)
            
            # Update state
            state.body_text = result.body_text
            state.messages.append({
                "role": "assistant",
                "content": f"Generated body text: {result.body_text}"
            })
            
            # Save final checkpoint
            self.save_checkpoint(state)
            
        except Exception as e:
            logger.error(f"Error in BodyGeneratorAgent: {str(e)}", exc_info=True)
            raise
        
        logger.debug(f"Body Generator - Output State Type: {type(state)}")
        logger.debug(f"Body Generator - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(IdentityAgentState)
        workflow.add_node("generate_body", self.run)
        workflow.set_entry_point("generate_body")
        workflow.add_edge("generate_body", "end")
        return workflow.compile() 