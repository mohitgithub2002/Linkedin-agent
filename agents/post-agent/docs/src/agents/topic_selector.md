# Topic Selector Agent Documentation (topic_selector.py)

## Overview

The `TopicSelectorAgent` is the first agent in the LinkedIn post generation workflow. It is responsible for either selecting a topic if none is provided, or creating a detailed brief for a given topic. This agent serves as the entry point for the entire workflow.

## Data Models

### KeyPoint Model

```python
class KeyPoint(BaseModel):
    heading: str = Field(description="The heading for this key point")
    content: str = Field(description="The content for this key point")
    optional_visual: str | None = Field(default=None, description="Optional visual suggestion")
    call_to_action: str | None = Field(default=None, description="Optional call to action")
```

Represents key points to cover in the post with:
- A heading for the point
- Detailed content
- Optional visual suggestion
- Optional call to action

### Brief Model

```python
class Brief(BaseModel):
    title: str = Field(description="The title of the post")
    target_audience: str = Field(description="The target audience for the post")
    key_points: List[KeyPoint] = Field(description="List of key points to cover")
    tone: str = Field(description="The tone to use in the post")
    hashtags: List[str] = Field(description="Relevant hashtags for the post")
```

Represents a structured brief for the post containing:
- A title
- Target audience information
- List of key points to cover
- Tone specification
- Relevant hashtags

### TopicBrief Model

```python
class TopicBrief(BaseModel):
    current_topic: str = Field(description="The selected topic for the LinkedIn post")
    brief: Brief = Field(description="A structured brief for the post")
```

The complete output model combining:
- The selected/provided topic
- A full brief for the post

## Agent Implementation

```python
class TopicSelectorAgent(BaseAgent):
    """Agent responsible for selecting topics for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("topic_selector")
        self.parser = JsonOutputParser(pydantic_object=TopicBrief)
```

The constructor initializes the agent with:
- Base agent configuration with name "topic_selector"
- JSON output parser configured for the TopicBrief model

### Prompt Creation

```python
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
```

This method creates:
- A prompt for topic brief creation when a topic is provided
- A prompt for topic selection and brief creation when no topic is provided

### Run Method

```python
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
```

The run method:
1. Handles state conversion if necessary
2. Checks if a topic is already provided
   - If yes, creates a brief for that topic
   - If no, selects a new topic and creates a brief
3. Updates the state with the topic and brief
4. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("select_topic", self.run)
    workflow.set_entry_point("select_topic")
    workflow.add_edge("select_topic", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for topic selection
- An edge to the end
- Entry point set to the topic selection node

## Functionality Flow

1. **Input**: Either receive a provided topic or operate with no topic
2. **Processing**:
   - If topic provided: Create a detailed brief for the given topic
   - If no topic: Select an engaging topic and create a brief
3. **Output**: Update state with the selected topic and brief data

## Integration Points

The Topic Selector Agent:
- Receives input from the main workflow orchestrator
- Outputs to the Research Agent
- Is the entry point for the entire post generation workflow

## Example Output

```json
{
  "current_topic": "AI in Content Marketing",
  "brief": {
    "title": "5 Ways AI is Revolutionizing Content Marketing Strategy in 2024",
    "target_audience": "Content marketing professionals, digital marketers, and business owners looking to leverage AI",
    "key_points": [
      {
        "heading": "AI-Powered Content Creation",
        "content": "How generative AI tools are streamlining content production and enabling scalability",
        "optional_visual": "Comparison chart of human vs. AI content creation time",
        "call_to_action": "What AI tools are you currently exploring for content creation?"
      },
      {
        "heading": "Personalization at Scale",
        "content": "Using AI to deliver hyper-personalized content experiences based on user behavior",
        "optional_visual": "User journey showing personalized touchpoints",
        "call_to_action": null
      }
    ],
    "tone": "Informative, forward-thinking, slightly technical but accessible",
    "hashtags": ["#AIMarketing", "#ContentStrategy", "#MarTech", "#DigitalTransformation"]
  }
}
``` 