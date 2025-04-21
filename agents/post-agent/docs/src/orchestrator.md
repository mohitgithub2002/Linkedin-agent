# Orchestrator Documentation (orchestrator.py)

## Overview

The `orchestrator.py` file is the central component of the LinkedIn post generation system. It manages the workflow of specialized agents, coordinates their execution sequence, and handles state transitions between agents. This file implements the core orchestration logic using LangGraph's `StateGraph`.

## Architecture

The orchestrator has three main responsibilities:

1. **Workflow Definition**: Define the sequence of agents and their relationships
2. **State Management**: Track and update state throughout the workflow
3. **Execution Control**: Execute the workflow and handle errors

## Key Components

### Imports and Environment Setup

```python
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
import asyncio
from langsmith import Client
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
import uuid
```

The file begins by importing necessary modules:
- LangChain/LangGraph components
- Agent classes
- Utility libraries
- LangSmith tracing components

### Logging Setup

```python
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set Python recursion limit to avoid hitting the limit in workflow execution
sys.setrecursionlimit(100)  # Increase from default to handle potential deep recursion
```

Sets up logging configuration and loads environment variables. The recursion limit is adjusted to handle complex workflow execution.

### LangSmith Integration

```python
# Initialize LangSmith client
langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
langsmith_project = os.getenv("LANGSMITH_PROJECT", "linkedin-post-generation")
langchain_endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
langchain_api_key = os.getenv("LANGCHAIN_API_KEY")

# Use the same API key for both if only one is provided
if langchain_api_key and not langsmith_api_key:
    langsmith_api_key = langchain_api_key
elif langsmith_api_key and not langchain_api_key:
    langchain_api_key = langsmith_api_key

# Initialize LangSmith client if credentials are available
langsmith_client = None
langsmith_tracing_enabled = False

if langsmith_api_key:
    try:
        langsmith_client = Client(
            api_key=langsmith_api_key,
            api_url=langchain_endpoint
        )
        # Set environment variables for LangChain tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        os.environ["LANGCHAIN_API_KEY"] = langchain_api_key
        langsmith_tracing_enabled = True
        logger.info(f"LangSmith client initialized with project: {langsmith_project}")
    except Exception as e:
        logger.warning(f"Failed to initialize LangSmith client: {str(e)}")
else:
    logger.warning("LANGSMITH_API_KEY not found. LangSmith tracing will be disabled.")
```

This section configures LangSmith integration for workflow tracing and monitoring. It handles:
- Fetching API keys from environment variables
- Initializing the LangSmith client
- Setting up environment variables for tracing
- Providing fallbacks if credentials aren't available

### Tracing Utilities

```python
# Safe version of wait_for_all_tracers that handles the case when tracing is disabled
async def safe_wait_for_tracers():
    """Safely wait for all tracers to complete, handling the case when tracing is disabled."""
    if not langsmith_tracing_enabled:
        logger.debug("LangSmith tracing is disabled, skipping wait_for_all_tracers")
        return
        
    try:
        # Only call wait_for_all_tracers if tracing is enabled
        await wait_for_all_tracers()
        logger.debug("Successfully waited for all tracers")
    except TypeError as e:
        if "NoneType" in str(e):
            logger.debug("No active tracers to wait for")
        else:
            logger.warning(f"Error waiting for tracers: {str(e)}")
    except Exception as e:
        logger.warning(f"Unexpected error waiting for tracers: {str(e)}")
```

A utility function that safely waits for LangSmith tracers to complete, with error handling for when tracing is disabled.

### Workflow Creation

```python
def create_workflow(llm: Optional[BaseChatModel] = None) -> StateGraph:
    """Create the main workflow graph for post generation."""
    # Initialize LLM if not provided
    if llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
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
```

This function:
1. Initializes the Google Gemini LLM if not provided
2. Creates instances of all specialized agents
3. Configures each agent with the LLM

```python
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
    
    # Compile the workflow
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow compiled successfully")
    return compiled_workflow
```

This part of the function defines the LangGraph workflow:
1. Creates a StateGraph with the AgentState model
2. Adds each agent as a node in the graph
3. Defines the linear sequence of execution with directed edges
4. Sets the topic selector as the entry point
5. Compiles the workflow for execution

### Post Generation Function

```python
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
```

The main function to generate a post:
1. Initializes the workflow
2. Creates the initial state with an optional topic

```python
        # Setup config for tracing
        config = {}
        
        # Set up LangSmith tracing if available
        if langsmith_tracing_enabled:
            run_id = str(uuid.uuid4())
            logger.info(f"LangSmith run ID: {run_id}")
            
            # Track metadata about the run
            metadata = {
                "topic": topic or "auto-selected",
                "workflow_type": "linkedin_post_generation",
                "version": "v1.3.24"
            }
            
            # Add additional metadata for better tracking
            if topic:
                metadata["topic_provided"] = "true"
            else:
                metadata["topic_provided"] = "false"
                
            # Add run configuration
            config = {
                "run_name": f"LinkedIn Post Generation - {topic or 'Auto Topic'}",
                "metadata": metadata
            }
```

Sets up LangSmith tracing configuration:
1. Creates a unique run ID
2. Tracks metadata about the generation run
3. Configures the run for LangSmith monitoring

```python
        # Execute workflow
        logger.info("Executing workflow")
        
        # Execute with tracing if enabled
        try:
            # Include config only if we have LangSmith enabled
            if langsmith_tracing_enabled:
                result = await workflow.ainvoke(initial_state, config=config)
                await safe_wait_for_tracers()
                logger.info("LangSmith tracing complete")
            else:
                # Execute without tracing config if LangSmith is not enabled
                result = await workflow.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            if langsmith_tracing_enabled:
                await safe_wait_for_tracers()
                logger.info("LangSmith tracing complete despite error")
            raise
```

Executes the workflow with the initial state:
1. Conditionally includes tracing configuration
2. Awaits workflow completion
3. Waits for tracers to finish if enabled
4. Handles execution errors

```python
        logger.debug(f"Workflow execution complete. Result type: {type(result)}")
        
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
    finally:
        # Ensure all traces are completed
        if langsmith_tracing_enabled:
            try:
                await safe_wait_for_tracers()
            except Exception as e:
                logger.warning(f"Error in finally block waiting for tracers: {str(e)}")
```

Handles workflow results and clean-up:
1. Converts the result to a standard dictionary
2. Validates that a post payload was generated
3. Returns the final post payload
4. Handles and logs errors
5. Ensures all traces are completed in the finally block

## Workflow Execution

The workflow execution follows this sequence:

1. **Initialization**: Create the StateGraph and initialize agents
2. **Topic Selection**: Choose or refine a topic through TopicSelectorAgent
3. **Research**: Gather relevant information through ResearchAgent
4. **Content Generation**: Create hook, body, and CTA sequentially
5. **Quality Assurance**: Assess the post quality through QAAgent
6. **Final Assembly**: Combine all components through FinalAssemblerAgent
7. **Result Validation**: Ensure the post_payload exists in the final state
8. **Return**: Provide the final post payload to the caller

## Error Handling

The orchestrator implements comprehensive error handling:

1. **Invalid LLM Configuration**: Checks for Google API key
2. **Workflow Execution Errors**: Catches and logs exceptions
3. **Missing Post Payload**: Validates the final result has the required payload
4. **Tracing Errors**: Safely handles issues with LangSmith tracing

## LangSmith Integration

The orchestrator provides detailed monitoring through LangSmith:

1. **Run Tracking**: Creates a unique ID for each run
2. **Metadata**: Captures topic information and version details
3. **Tracing**: Records all LLM interactions and agent transitions
4. **Error Tracking**: Ensures traces are completed even when errors occur 