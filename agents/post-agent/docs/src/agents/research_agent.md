# Research Agent Documentation (research_agent.py)

## Overview

The `ResearchAgent` is the second agent in the LinkedIn post generation workflow. It is responsible for gathering relevant research, facts, statistics, and supporting information related to the selected topic. This information will be used by subsequent agents to create rich, substantiated content.

## Data Models

### ResearchItem Model

```python
class ResearchItem(BaseModel):
    source: str = Field(description="The source of the information")
    snippet: str = Field(description="The relevant information from the source")
```

Represents a single research item with:
- A source identifier/URL
- A relevant snippet of information

### ResearchResult Model

```python
class ResearchResult(BaseModel):
    items: List[ResearchItem] = Field(description="List of research items found")
```

Container for multiple research items.

## Agent Implementation

```python
class ResearchAgent(BaseAgent):
    """Agent responsible for gathering research and supporting content."""
    
    def __init__(self):
        tools = [
            Tool(
                name="web_search",
                func=self._web_search,
                description="Search the web for relevant information"
            )
        ]
        super().__init__("research_agent", tools)
        self.parser = JsonOutputParser(pydantic_object=ResearchResult)
```

The constructor initializes the agent with:
- A web search tool for information gathering
- Base agent configuration with name "research_agent"
- JSON output parser configured for the ResearchResult model

### Web Search Tool

```python
def _web_search(self, query: str) -> str:
    """Perform a web search and extract relevant information."""
    # This is a simplified version. In production, you'd want to use a proper search API
    try:
        response = requests.get(f"https://www.google.com/search?q={query}")
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='g')
        return "\n".join([result.get_text() for result in results[:3]])
    except Exception as e:
        return f"Error performing web search: {str(e)}"
```

A tool that:
- Takes a search query
- Makes a request to Google
- Parses the response with BeautifulSoup
- Extracts relevant information from the results
- Returns a text summary of findings

### Prompt Creation

```python
def create_prompt(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are a research assistant for LinkedIn content creation. Your task is to:
        1. Gather relevant facts, statistics, and supporting information
        2. Verify the credibility of sources
        3. Extract key insights that support the main topic
        
        Format your findings as a JSON object with the following structure:
        {{
            "items": [
                {{
                    "source": "The source of the information",
                    "snippet": "The relevant information from the source"
                }}
            ]
        }}"""),
        ("human", "Research information about: {topic}")
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a research assistant
- Defines the task requirements
- Specifies the output format
- Provides a template for the human query

### Run Method

```python
async def run(self, state: AgentState) -> AgentState:
    logger.debug(f"Research Agent - Input State Type: {type(state)}")
    logger.debug(f"Research Agent - Input State Content: {state}")
    
    # Convert state dictionary to AgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to AgentState")
        state = AgentState(**state)
        logger.debug(f"Converted State Type: {type(state)}")
        logger.debug(f"Converted State Content: {state}")
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic selected for research")
        
    prompt = self.create_prompt()
    chain = prompt | self.llm | self.parser
    
    # Get research data
    result = await chain.ainvoke({"topic": state.current_topic})
    logger.debug(f"Research Result: {result}")
    
    # Convert result to ResearchResult if it's a dictionary
    if isinstance(result, dict):
        result = ResearchResult(**result)
    
    # Update state with all research items
    for item in result.items:
        state.research_data.append({
            "source": item.source,
            "snippet": item.snippet
        })
    
    state.messages.append({
        "role": "assistant",
        "content": f"Research completed for topic: {state.current_topic}. Found {len(result.items)} items."
    })
    
    logger.debug(f"Research Agent - Output State Type: {type(state)}")
    logger.debug(f"Research Agent - Output State Content: {state}")
    return state
```

The run method:
1. Validates the input state has a topic
2. Creates the prompt and chain
3. Invokes the LLM to generate research data
4. Parses the structured research results
5. Updates the state with the research items
6. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("research", self.run)
    workflow.set_entry_point("research")
    workflow.add_edge("research", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for research
- An edge to the end
- Entry point set to the research node

## Functionality Flow

1. **Input**: Receives a state with a selected topic
2. **Processing**:
   - Creates a research prompt for the topic
   - Uses the LLM to generate research items
   - Can use the web_search tool if needed
3. **Output**: Updates state with research_data containing facts and information

## Integration Points

The Research Agent:
- Receives input from the Topic Selector Agent
- Outputs to the Hook Generator Agent
- Uses the research_data field in the AgentState

## Example Output

```json
{
  "items": [
    {
      "source": "Harvard Business Review, 2023",
      "snippet": "According to recent studies, companies implementing AI in content marketing see a 40% increase in engagement and a 37% decrease in content production costs."
    },
    {
      "source": "Content Marketing Institute",
      "snippet": "73% of content marketers are now using AI for content creation, up from 45% in 2022."
    },
    {
      "source": "Gartner Research",
      "snippet": "By 2025, an estimated 30% of all marketing content will be produced by AI, with human oversight focusing on strategy and editing."
    },
    {
      "source": "McKinsey Digital",
      "snippet": "AI-driven personalization in content marketing has shown to increase conversion rates by up to 25% across industries."
    }
  ]
} 