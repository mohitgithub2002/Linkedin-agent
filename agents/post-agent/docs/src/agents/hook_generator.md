# Hook Generator Agent Documentation (hook_generator.py)

## Overview

The `HookGeneratorAgent` is the third agent in the LinkedIn post generation workflow. It is responsible for creating an engaging hook (opening) for the post that captures attention and encourages readers to continue reading. A good hook is crucial for LinkedIn content as it determines whether viewers will stop scrolling to read the full post.

## Data Models

### HookResult Model

```python
class HookResult(BaseModel):
    hook_text: str = Field(description="The generated hook text for the LinkedIn post")
    tone: str = Field(description="The tone used in the hook")
    target_audience: str = Field(description="The target audience for the hook")
```

This model represents the generated hook with:
- The actual hook text to be used in the post
- Information about the tone used in the hook
- The target audience the hook is designed to appeal to

## Agent Implementation

```python
class HookGeneratorAgent(BaseAgent):
    """Agent responsible for generating engaging hooks for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("hook_generator")
        self.parser = JsonOutputParser(pydantic_object=HookResult)
```

The constructor initializes the agent with:
- Base agent configuration with name "hook_generator"
- JSON output parser configured for the HookResult model

### Prompt Creation

```python
def create_prompt(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are a professional LinkedIn content creator. Your task is to:
        1. Create an engaging hook for a LinkedIn post
        2. Ensure the hook captures attention and encourages reading
        3. Match the tone and target audience of the post
        
        Consider:
        - The main topic
        - The target audience
        - Current trends
        - Professional tone
        
        Format your response as a JSON object with the following structure:
        {{
            "hook_text": "The engaging hook text",
            "tone": "The tone used in the hook",
            "target_audience": "The target audience for the hook"
        }}"""),
        ("human", "Generate a hook for a post about: {topic}")
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a LinkedIn content creator
- Defines what makes a good hook
- Provides guidance on factors to consider
- Specifies the output format
- Provides a template for the human query

### Run Method

```python
async def run(self, state: AgentState) -> AgentState:
    logger.debug(f"Hook Generator - Input State Type: {type(state)}")
    logger.debug(f"Hook Generator - Input State Content: {state}")
    
    # Convert state dictionary to AgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to AgentState")
        state = AgentState(**state)
        logger.debug(f"Converted State Type: {type(state)}")
        logger.debug(f"Converted State Content: {state}")
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic selected for hook generation")
        
    prompt = self.create_prompt()
    chain = prompt | self.llm | self.parser
    
    # Get hook text
    result = await chain.ainvoke({"topic": state.current_topic})
    logger.debug(f"Hook Generation Result: {result}")
    
    # Convert result to HookResult if it's a dictionary
    if isinstance(result, dict):
        result = HookResult(**result)
    
    # Update state
    state.hook_text = result.hook_text
    state.messages.append({
        "role": "assistant",
        "content": f"Generated hook: {result.hook_text}\nTone: {result.tone}\nTarget Audience: {result.target_audience}"
    })
    
    logger.debug(f"Hook Generator - Output State Type: {type(state)}")
    logger.debug(f"Hook Generator - Output State Content: {state}")
    return state
```

The run method:
1. Validates the input state has a topic
2. Creates the prompt and chain
3. Invokes the LLM to generate a hook
4. Parses the structured hook result
5. Updates the state with the hook text and metadata
6. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_hook", self.run)
    workflow.set_entry_point("generate_hook")
    workflow.add_edge("generate_hook", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for hook generation
- An edge to the end
- Entry point set to the hook generation node

## Functionality Flow

1. **Input**: Receives a state with a selected topic (and possibly research data)
2. **Processing**:
   - Creates a prompt for hook generation based on the topic
   - Uses the LLM to generate an engaging hook
   - Determines appropriate tone and target audience
3. **Output**: Updates state with the hook text and additional metadata

## Hook Characteristics

The Hook Generator creates hooks that:
- Grab attention in the first few seconds
- Create curiosity or interest
- Establish relevance to the target audience
- Set the tone for the rest of the post
- Preview the value proposition of the content
- Are concise and impactful

## Integration Points

The Hook Generator Agent:
- Receives input from the Research Agent
- Outputs to the Body Generator Agent
- Updates the hook_text field in the AgentState

## Example Output

```json
{
  "hook_text": "Did you know that companies using AI in content marketing see a 40% boost in engagement while cutting costs by 37%? The future of marketing isn't coming—it's already here.",
  "tone": "Informative with a touch of urgency",
  "target_audience": "Marketing professionals and business leaders interested in AI technology"
}
```

## Hook Types Generated

The agent can generate various types of hooks:
1. **Statistical hooks**: Leading with a surprising statistic
2. **Question hooks**: Engaging the reader with a thought-provoking question
3. **Challenge hooks**: Challenging conventional wisdom or assumptions
4. **Story hooks**: Beginning with a brief, relatable story
5. **Quote hooks**: Using a relevant, impactful quote
6. **Problem-solution hooks**: Identifying a pain point and hinting at a solution 