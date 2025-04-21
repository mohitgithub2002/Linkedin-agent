from typing import Dict, Any, Optional, List, TypedDict, Literal
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from .agents.base import AgentState, BaseAgent
from .agents.topic_selector import TopicSelectorAgent
from .agents.research_agent import ResearchAgent
from .agents.hook_generator import HookGeneratorAgent
from .agents.body_generator import BodyGeneratorAgent
from .agents.cta_generator import CTAGeneratorAgent
from .agents.qa_agent import QAAgent
from .agents.final_assembler import FinalAssemblerAgent
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set Python recursion limit to avoid hitting the limit in workflow execution
sys.setrecursionlimit(100)  # Increase from default to handle potential deep recursion

def create_workflow(llm: Optional[BaseChatModel] = None) -> StateGraph:
    """Create the main workflow graph for post generation."""
    # Initialize LLM if not provided
    if llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=api_key,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        )
        logger.info("Initialized default LLM")
    
    # Initialize agents
    topic_selector = TopicSelectorAgent()
    topic_selector.set_llm(llm)
    
    researcher = ResearchAgent()
    researcher.set_llm(llm)
    
    hook_generator = HookGeneratorAgent()
    hook_generator.set_llm(llm)
    
    body_generator = BodyGeneratorAgent()
    body_generator.set_llm(llm)
    
    cta_generator = CTAGeneratorAgent()
    cta_generator.set_llm(llm)
    
    qa_agent = QAAgent()
    qa_agent.set_llm(llm)
    
    final_assembler = FinalAssemblerAgent()
    final_assembler.set_llm(llm)
    
    logger.info("All agents initialized with LLM")
    
    # Define the workflow
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("select_topic", topic_selector.run)
    workflow.add_node("research", researcher.run)
    workflow.add_node("generate_hook", hook_generator.run)
    workflow.add_node("generate_body", body_generator.run)
    workflow.add_node("generate_cta", cta_generator.run)
    workflow.add_node("qa_check", qa_agent.run)
    workflow.add_node("assemble_post", final_assembler.run)
    
    logger.info("Added all nodes to workflow graph")
    
    # Define edges
    workflow.add_edge("select_topic", "research")
    workflow.add_edge("research", "generate_hook")
    workflow.add_edge("generate_hook", "generate_body")
    workflow.add_edge("generate_body", "generate_cta")
    workflow.add_edge("generate_cta", "qa_check")
    workflow.add_edge("qa_check", "assemble_post")
    workflow.add_edge("assemble_post", END)
    
    logger.info("Added all edges to workflow graph")
    
    # Set entry point
    workflow.set_entry_point("select_topic")
    logger.info("Set entry point to 'select_topic'")
    
    # Compile the workflow - remove unsupported parameters
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compiled successfully")
    return compiled_workflow

async def generate_post(topic: Optional[str] = None) -> Dict[str, Any]:
    """Generate a LinkedIn post on the given topic."""
    try:
        logger.info(f"Starting post generation for topic: {topic}")
        
        # Initialize workflow
        workflow = create_workflow()
        
        # Create initial state
        initial_state = AgentState()
        if topic:
            initial_state.current_topic = topic
            logger.info(f"Initialized state with topic: {topic}")
        
        # Execute workflow
        logger.info("Executing workflow")
        result = await workflow.ainvoke(initial_state)
        logger.debug(f"Workflow execution complete. Result type: {type(result)}")
        logger.debug(f"Result content: {result}")
        
        # Convert AddableValuesDict to a regular dict and access state keys
        # In LangGraph, the result is an AddableValuesDict, not an AgentState
        result_dict = dict(result)
        logger.debug(f"Converted result to dict. Keys: {result_dict.keys()}")
        
        # Check if the final state has a post_payload
        if "post_payload" not in result_dict or not result_dict["post_payload"]:
            logger.error("Workflow did not produce a post_payload")
            raise ValueError("Failed to generate post: No post payload in result")
        
        logger.info("Post generation completed successfully")
        return result_dict["post_payload"]
    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}", exc_info=True)
        raise ValueError(f"Error generating post: {str(e)}") 