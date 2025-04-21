# Base Agent Documentation (base.py)

## Overview

The `base.py` file defines the foundation for all specialized agents in the LinkedIn post generation system. It contains:
1. The `AgentState` data model for tracking workflow state
2. The abstract `BaseAgent` class that all specialized agents inherit from

## AgentState Model

The `AgentState` class is a Pydantic model that serves as the state container for the entire workflow. It holds all data generated throughout the post creation process.

```python
class AgentState(BaseModel):
    """State model for agent workflow."""
    current_topic: Optional[str] = Field(default=None, description="Current topic being processed")
    hook_text: Optional[str] = Field(default=None, description="Generated hook text")
    body_text: Optional[str] = Field(default=None, description="Generated body text")
    cta_text: Optional[str] = Field(default=None, description="Generated call-to-action text")
    research_data: List[Dict[str, str]] = Field(default_factory=list, description="Research data collected")
    messages: List[Dict[str, str]] = Field(default_factory=list, description="Chat messages")
    qa_feedback: Optional[str] = Field(default=None, description="QA feedback on the post")
    qa_suggestions: List[str] = Field(default_factory=list, description="QA suggestions for improvement")
    qa_score: Optional[int] = Field(default=None, description="QA score from 1-10")
    qa_issues: List[str] = Field(default_factory=list, description="QA identified issues")
    post_payload: Optional[Dict[str, Any]] = Field(default=None, description="Final assembled post payload")
    image_url: Optional[str] = Field(default=None, description="URL for post image")
```

### State Fields

| Field Name       | Type                  | Description                                    |
|------------------|------------------------|------------------------------------------------|
| current_topic    | Optional[str]         | The topic for the LinkedIn post                |
| hook_text        | Optional[str]         | The attention-grabbing opening text            |
| body_text        | Optional[str]         | The main content of the post                   |
| cta_text         | Optional[str]         | The call-to-action text                        |
| research_data    | List[Dict[str, str]]  | Collected research information                 |
| messages         | List[Dict[str, str]]  | Chat messages throughout the process           |
| qa_feedback      | Optional[str]         | QA agent's overall feedback                    |
| qa_suggestions   | List[str]             | Specific improvement suggestions               |
| qa_score         | Optional[int]         | Quality score (1-10)                           |
| qa_issues        | List[str]             | Specific issues identified                     |
| post_payload     | Optional[Dict[str, Any]] | Final assembled post with all components    |
| image_url        | Optional[str]         | URL for any post image                         |

## BaseAgent Class

The `BaseAgent` class is the abstract base class for all specialized agents.

```python
class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, tools: Optional[List[BaseTool]] = None):
        self.name = name
        self.tools = tools or []
        self.tool_node = ToolNode(self.tools) if self.tools else None
        
        # Initialize LLM with default configuration
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        )
        
        logger.info(f"Initialized {self.name} agent with {len(self.tools)} tools and LLM configured")
```

The constructor initializes the agent with:
- A name identifier
- Optional list of tools
- A configured LLM (Google Gemini by default)

### Core Methods

#### set_llm Method

```python
def set_llm(self, llm: BaseChatModel):
    """Set the language model for the agent."""
    if not isinstance(llm, BaseChatModel):
        raise ValueError("LLM must be an instance of BaseChatModel")
    self.llm = llm
    logger.debug(f"Set custom LLM for {self.name} agent")
```

Allows setting a custom language model for the agent, with type checking to ensure it's a proper LangChain LLM.

#### add_tool Method

```python
def add_tool(self, tool: BaseTool):
    """Add a tool to the agent's toolkit."""
    if not isinstance(tool, BaseTool):
        raise ValueError("Tool must be an instance of BaseTool")
    self.tools.append(tool)
    self.tool_node = ToolNode(self.tools)
    logger.debug(f"Added tool {tool.name} to {self.name} agent")
```

Adds a new tool to the agent's toolkit and updates the tool node.

#### create_chain Method

```python
def create_chain(self, prompt: ChatPromptTemplate) -> Any:
    """Create a chain with the LLM and parser."""
    if not self.llm:
        raise ValueError("LLM not initialized. Call set_llm() first.")
    return prompt | self.llm
```

Creates a LangChain chain by combining the prompt template with the LLM.

#### create_prompt Method

```python
def create_prompt(self, system_prompt: str) -> ChatPromptTemplate:
    """Create a chat prompt template for the agent."""
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
```

Utility method to create a chat prompt template with a system message and a human input placeholder.

### Abstract Methods

The following methods must be implemented by all subclasses:

```python
async def run(self, state: AgentState) -> AgentState:
    """Run the agent's main logic."""
    raise NotImplementedError("Subclasses must implement run method")
    
def get_graph(self) -> Graph:
    """Get the agent's workflow graph."""
    raise NotImplementedError("Subclasses must implement get_graph method")
```

- **run**: The main method that executes the agent's logic and updates the state
- **get_graph**: Returns a LangGraph workflow graph for the agent

## Usage in Specialized Agents

All specialized agents in the system inherit from `BaseAgent`:

```python
class TopicSelectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("topic_selector")
        # Specialized implementation...
        
    async def run(self, state: AgentState) -> AgentState:
        # Implement specific run logic
        
    def get_graph(self) -> Graph:
        # Implement specific graph creation
```

Each specialized agent:
1. Inherits basic functionality from BaseAgent
2. Implements its own run method with specialized logic
3. Optionally overrides other methods as needed
4. Maintains and updates the shared AgentState 