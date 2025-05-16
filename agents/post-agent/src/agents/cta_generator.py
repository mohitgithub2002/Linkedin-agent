from typing import Any, Dict, List, Union
from .base import BaseAgent, AgentState
from .identity_agent import IdentityAgentState
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
        
    def create_prompt(self, identity_spec: Any) -> ChatPromptTemplate:
        # Convert complex objects to simple strings to avoid formatting issues
        voice_str = str(identity_spec.voice).replace("{", "{{").replace("}", "}}")
        pillars_str = str(identity_spec.pillars_ranked).replace("{", "{{").replace("}", "}}")
        cta_style = str(identity_spec.cta_style).replace("{", "{{").replace("}", "}}")
        
        # Create a simple system message with no JSON example
        system_message = f"""You are a professional LinkedIn content creator for {identity_spec.creator}. 

Your task is to create an engaging call-to-action (CTA) for a LinkedIn post that:
1. Aligns with the creator's brand identity
2. Corresponds with the post's content and tone
3. Is clear, actionable, and compelling
4. Follows the creator's CTA style: {cta_style}
5. Maintains the creator's voice: {voice_str}

Consider these elements:
- The post's main topic and content
- The target audience
- The desired action
- The tone of the post
- The creator's brand pillars: {pillars_str}
- The creator's promise: {identity_spec.promise}

Output a JSON with these fields:
- cta_text: The call-to-action text as a string
- action_type: A SINGLE word or phrase describing the action type (e.g. "comment", "share"), not a list
- urgency_level: A SINGLE word describing the urgency level (e.g. "high", "medium", "low"), not a list"""

        # Create a completely separate human message template
        human_message = "Generate a CTA for a post about: {topic}\nContent: {content}"
        
        # Create template with simple parts
        template = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
        
        logger.debug(f"Created CTA prompt template with variables: {template.input_variables}")
        return template
    
    async def run(self, state: IdentityAgentState) -> IdentityAgentState:
        logger.debug(f"CTA Generator - Input State Type: {type(state)}")
        logger.debug(f"CTA Generator - Input State Content: {state}")
        
        # Convert state dictionary to IdentityAgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to IdentityAgentState")
            state = IdentityAgentState(**state)
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
            
        if not state.identity_spec:
            logger.error("No identity spec found in state")
            raise ValueError("Identity specification required for CTA generation")
            
        # Create prompt
        prompt = self.create_prompt(state.identity_spec)
        logger.debug(f"Prompt variables: {prompt.input_variables}")
        chain = prompt | self.llm | self.parser
        
        try:
            # Log the inputs
            logger.debug(f"Invoking chain with topic: {state.current_topic}")
            logger.debug(f"Content length: {len(state.body_text)}")
            
            # Get CTA text
            result = await chain.ainvoke({
                "topic": state.current_topic,
                "content": state.body_text
            })
            logger.debug(f"CTA Generation Result: {result}")
            
            # Handle case where fields might be lists instead of strings
            if isinstance(result, dict):
                for field in ["action_type", "urgency_level", "cta_text"]:
                    if field in result and isinstance(result[field], list):
                        logger.warning(f"{field} returned as a list: {result[field]}. Converting to string.")
                        result[field] = ", ".join(result[field])
            
            # Convert result to CTAResult if it's a dictionary
            if isinstance(result, dict):
                result = CTAResult(**result)
                
            # Validate CTA against identity rules
            if state.validators and "body" in state.validators:  # Reuse body validator for CTA
                is_valid, error_msg = state.validators["body"](result.cta_text)
                if not is_valid:
                    logger.warning(f"CTA validation failed: {error_msg}")
                    # Retry with more specific guidance
                    prompt = self.create_prompt(state.identity_spec)
                    chain = prompt | self.llm | self.parser
                    retry_result = await chain.ainvoke({
                        "topic": state.current_topic,
                        "content": state.body_text,
                        "error": f"Previous CTA failed validation: {error_msg}. Please try again."
                    })
                    
                    # Handle case where fields might be lists in retry
                    if isinstance(retry_result, dict):
                        for field in ["action_type", "urgency_level", "cta_text"]:
                            if field in retry_result and isinstance(retry_result[field], list):
                                logger.warning(f"{field} returned as a list in retry: {retry_result[field]}. Converting to string.")
                                retry_result[field] = ", ".join(retry_result[field])
                        
                        result = CTAResult(**retry_result)
                        
            # Score tone if validator available
            if state.validators and "tone" in state.validators:
                tone_score = state.validators["tone"](result.cta_text)
                logger.info(f"CTA tone score: {tone_score}")
                if tone_score < 0.6:  # Threshold for acceptable tone
                    logger.warning("CTA tone score too low, regenerating")
                    prompt = self.create_prompt(state.identity_spec)
                    chain = prompt | self.llm | self.parser
                    retry_result = await chain.ainvoke({
                        "topic": state.current_topic,
                        "content": state.body_text,
                        "error": "Previous CTA tone score was too low. Please improve readability and engagement."
                    })
                    
                    # Handle case where fields might be lists in tone retry
                    if isinstance(retry_result, dict):
                        for field in ["action_type", "urgency_level", "cta_text"]:
                            if field in retry_result and isinstance(retry_result[field], list):
                                logger.warning(f"{field} returned as a list in tone retry: {retry_result[field]}. Converting to string.")
                                retry_result[field] = ", ".join(retry_result[field])
                        
                        result = CTAResult(**retry_result)
            
            # Update state
            state.cta_text = result.cta_text
            state.messages.append({
                "role": "assistant",
                "content": f"Generated CTA: {result.cta_text}\nAction Type: {result.action_type}\nUrgency Level: {result.urgency_level}"
            })
            
            # Save final checkpoint
            self.save_checkpoint(state)
            
        except Exception as e:
            logger.error(f"Error in CTAGeneratorAgent: {str(e)}", exc_info=True)
            raise
        
        logger.debug(f"CTA Generator - Output State Type: {type(state)}")
        logger.debug(f"CTA Generator - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(IdentityAgentState)
        workflow.add_node("generate_cta", self.run)
        workflow.set_entry_point("generate_cta")
        workflow.add_edge("generate_cta", "end")
        return workflow.compile() 