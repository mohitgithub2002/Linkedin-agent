from typing import Any, Dict, List, Union
from .base import BaseAgent, AgentState
from .identity_agent import IdentityAgentState
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
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
        
    def create_prompt(self, identity_spec: Any) -> ChatPromptTemplate:
        """Create a simplified prompt with no JSON structure in the system message."""
        # Escape the hook templates
        escaped_templates = str(identity_spec.hook_templates).replace("{", "{{").replace("}", "}}")
        
        # Convert complex objects to simple strings to avoid formatting issues
        voice_str = str(identity_spec.voice).replace("{", "{{").replace("}", "}}")
        pillars_str = str(identity_spec.pillars_ranked).replace("{", "{{").replace("}", "}}")
        
        # Create a very simple system message with no JSON example
        system_message = f"""You are a professional LinkedIn content creator for {identity_spec.creator}. 

Your task is to create an engaging hook for a LinkedIn post that:
1. Aligns with the creator's brand identity
2. Captures attention and encourages reading
3. Matches appropriate tone and target audience
4. Follows voice guidelines: {voice_str}
5. Uses one of these templates: {escaped_templates}

Consider these elements:
- Creator's brand pillars: {pillars_str}
- Creator's promise: {identity_spec.promise}

Output a JSON with these fields:
- hook_text: The engaging hook text as a string
- tone: A SINGLE word or phrase describing the tone (e.g. "professional" or "conversational"), not a list
- target_audience: The target audience for the hook as a string"""

        # Create a completely separate human message template
        human_message = "Generate a hook for a post about: {topic}"
        
        # Create template with simple parts
        template = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
        
        logger.debug(f"Created prompt template with variables: {template.input_variables}")
        return template
    
    async def run(self, state: IdentityAgentState) -> IdentityAgentState:
        logger.debug(f"Hook Generator - Input State Type: {type(state)}")
        logger.debug(f"Hook Generator - Input State Content: {state}")
        
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
            raise ValueError("No topic selected for hook generation")
            
        if not state.identity_spec:
            logger.error("No identity spec found in state")
            raise ValueError("Identity specification required for hook generation")
            
        # Create the prompt and chain
        prompt = self.create_prompt(state.identity_spec)
        logger.debug(f"Prompt variables: {prompt.input_variables}")
        chain = prompt | self.llm | self.parser
        
        # Get hook text with only the topic variable
        logger.debug(f"Invoking chain with topic: {state.current_topic}")
        logger.debug(f"Input to chain: {{'topic': '{state.current_topic}'}}")
        
        try:
            result = await chain.ainvoke({"topic": state.current_topic})
            logger.debug(f"Hook Generation Result: {result}")
            
            # Handle case where tone might be a list instead of a string
            if isinstance(result, dict) and "tone" in result and isinstance(result["tone"], list):
                logger.warning(f"Tone returned as a list: {result['tone']}. Converting to string.")
                result["tone"] = ", ".join(result["tone"])
            
            # Convert result to HookResult if it's a dictionary
            if isinstance(result, dict):
                result = HookResult(**result)
            
        except Exception as e:
            logger.error(f"Error invoking hook generation chain: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate hook: {str(e)}")
            
        # Validate hook against identity rules
        if state.validators and "hook" in state.validators:
            is_valid, error_msg = state.validators["hook"](result.hook_text)
            if not is_valid:
                logger.warning(f"Hook validation failed: {error_msg}")
                # Retry with more specific guidance
                prompt = self.create_prompt(state.identity_spec)
                chain = prompt | self.llm | self.parser
                result = await chain.ainvoke({
                    "topic": state.current_topic,
                    "error": f"Previous hook failed validation: {error_msg}. Please try again."
                })
                if isinstance(result, dict):
                    # Handle case where tone might be a list instead of a string
                    if "tone" in result and isinstance(result["tone"], list):
                        logger.warning(f"Tone returned as a list: {result['tone']}. Converting to string.")
                        result["tone"] = ", ".join(result["tone"])
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
        workflow = StateGraph(IdentityAgentState)
        workflow.add_node("generate_hook", self.run)
        workflow.set_entry_point("generate_hook")
        workflow.add_edge("generate_hook", "end")
        return workflow.compile() 