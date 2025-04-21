# Body Generator Agent Documentation (body_generator.py)

## Overview

The `BodyGeneratorAgent` is the fourth agent in the LinkedIn post generation workflow. It is responsible for generating the main body content of the post, which provides the substantive information, insights, and value to the reader. The body builds upon the hook and incorporates the research data to create compelling, informative content.

## Data Models

### BodyResult Model

```python
class BodyResult(BaseModel):
    body_text: str = Field(description="The generated body text for the LinkedIn post")
    key_points: List[str] = Field(description="List of key points covered in the body")
    tone: str = Field(description="The tone used in the body")
```

This model represents the generated body content with:
- The main body text to be used in the post
- A list of key points covered in the content
- Information about the tone used in the body

## Agent Implementation

```python
class BodyGeneratorAgent(BaseAgent):
    """Agent responsible for generating the main body content for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("body_generator")
        self.parser = JsonOutputParser(pydantic_object=BodyResult)
```

The constructor initializes the agent with:
- Base agent configuration with name "body_generator"
- JSON output parser configured for the BodyResult model

### Prompt Creation

```python
def create_prompt(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are a professional LinkedIn content creator. Your task is to:
        1. Create engaging body content for a LinkedIn post
        2. Ensure the content flows naturally from the hook
        3. Include relevant research and insights
        4. Maintain a professional and engaging tone
        
        Consider:
        - The hook and its tone
        - Research data and insights
        - Target audience
        - Professional value
        
        Format your response as a JSON object with the following structure:
        {{
            "body_text": "The main body content",
            "key_points": ["Key point 1", "Key point 2", ...],
            "tone": "The tone used in the body"
        }}"""),
        ("human", "Generate body content for a post about: {topic}\nHook: {hook}\nResearch: {research}")
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a LinkedIn content creator
- Defines what makes good body content
- Provides guidance on factors to consider
- Specifies the output format
- Provides a template for the human query that includes the topic, hook, and research

### Run Method

```python
async def run(self, state: AgentState) -> AgentState:
    logger.debug(f"Body Generator - Input State Type: {type(state)}")
    logger.debug(f"Body Generator - Input State Content: {state}")
    
    # Convert state dictionary to AgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to AgentState")
        state = AgentState(**state)
        logger.debug(f"Converted State Type: {type(state)}")
        logger.debug(f"Converted State Content: {state}")
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic selected for body generation")
        
    if not state.hook_text:
        logger.error("No hook found in state")
        raise ValueError("No hook generated for body generation")
        
    prompt = self.create_prompt()
    chain = prompt | self.llm | self.parser
    
    # Get body text
    research_context = "\n".join([f"{item['source']}: {item['snippet']}" 
                                for item in state.research_data])
    result = await chain.ainvoke({
        "topic": state.current_topic,
        "hook": state.hook_text,
        "research": research_context
    })
    logger.debug(f"Body Generation Result: {result}")
    
    # Convert result to BodyResult if it's a dictionary
    if isinstance(result, dict):
        result = BodyResult(**result)
    
    # Update state
    state.body_text = result.body_text
    state.messages.append({
        "role": "assistant",
        "content": f"Generated body content: {result.body_text}\nKey Points: {', '.join(result.key_points)}\nTone: {result.tone}"
    })
    
    logger.debug(f"Body Generator - Output State Type: {type(state)}")
    logger.debug(f"Body Generator - Output State Content: {state}")
    return state
```

The run method:
1. Validates the input state has a topic and hook
2. Creates the prompt and chain
3. Formats the research data into a usable context string
4. Invokes the LLM to generate body content based on topic, hook, and research
5. Parses the structured body result
6. Updates the state with the body text and metadata
7. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_body", self.run)
    workflow.set_entry_point("generate_body")
    workflow.add_edge("generate_body", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for body generation
- An edge to the end
- Entry point set to the body generation node

## Body Content Characteristics

The Body Generator creates content that:
- Expands on the promise of the hook
- Provides substantive value to the reader
- Incorporates research data and insights
- Maintains a professional and engaging tone
- Follows a logical structure
- Uses appropriate formatting for LinkedIn (paragraphs, bullet points, etc.)
- Balances readability with depth of information

## Functionality Flow

1. **Input**: Receives a state with a selected topic, hook, and research data
2. **Processing**:
   - Creates a prompt for body generation using topic, hook, and research
   - Formats research data for context
   - Uses the LLM to generate comprehensive body content
   - Extracts key points and tone information
3. **Output**: Updates state with the body text and additional metadata

## Integration Points

The Body Generator Agent:
- Receives input from the Hook Generator Agent
- Outputs to the CTA Generator Agent
- Uses the topic, hook_text, and research_data fields from the AgentState
- Updates the body_text field in the AgentState

## Example Output

```json
{
  "body_text": "The AI revolution in content marketing is transforming how businesses connect with their audiences. According to Harvard Business Review, companies implementing AI solutions are seeing a 40% increase in engagement while simultaneously reducing production costs by 37%.\n\nThis shift isn't just about efficiency—it's about effectiveness. The Content Marketing Institute reports that 73% of content marketers have already adopted AI for creation processes, a dramatic increase from just 45% last year.\n\nWhat's driving this rapid adoption? Three key factors:\n\n1. **Scale without sacrifice**: AI enables marketers to produce more content without compromising quality\n2. **Data-driven personalization**: AI analyzes user behavior to deliver highly relevant content\n3. **Optimization through iteration**: AI continuously learns and improves based on performance metrics\n\nAs Gartner Research predicts, by 2025, nearly a third of all marketing content will be AI-generated, with human marketers focusing on strategy and oversight rather than production.",
  "key_points": [
    "AI increases engagement while reducing costs",
    "Adoption of AI in content marketing has risen dramatically",
    "AI enables scale, personalization, and continuous optimization",
    "Human marketers are shifting to strategic roles"
  ],
  "tone": "Informative and authoritative with a forward-looking perspective"
}
``` 