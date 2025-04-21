# CTA Generator Agent Documentation (cta_generator.py)

## Overview

The `CTAGeneratorAgent` is the fifth agent in the LinkedIn post generation workflow. It is responsible for creating a compelling call-to-action (CTA) that concludes the post and encourages reader engagement. An effective CTA drives interaction with the post through comments, shares, and connections, which is critical for LinkedIn's algorithm visibility.

## Data Models

### CTAResult Model

```python
class CTAResult(BaseModel):
    cta_text: str = Field(description="The generated call-to-action text")
    action_type: str = Field(description="The type of action being requested")
    urgency_level: str = Field(description="The level of urgency in the CTA")
```

This model represents the generated CTA with:
- The actual CTA text to be used in the post
- The type of action being requested from readers
- The level of urgency conveyed in the CTA

## Agent Implementation

```python
class CTAGeneratorAgent(BaseAgent):
    """Agent responsible for generating compelling calls-to-action for LinkedIn posts."""
    
    def __init__(self):
        super().__init__("cta_generator")
        self.parser = JsonOutputParser(pydantic_object=CTAResult)
```

The constructor initializes the agent with:
- Base agent configuration with name "cta_generator"
- JSON output parser configured for the CTAResult model

### Prompt Creation

```python
def create_prompt(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are a professional LinkedIn content creator. Your task is to:
        1. Create an engaging call-to-action (CTA) for a LinkedIn post
        2. Ensure the CTA aligns with the post's content and tone
        3. Make the CTA clear, actionable, and compelling
        
        Consider:
        - The post's main topic and content
        - The target audience
        - The desired action
        - The tone of the post
        
        Format your response as a JSON object with the following structure:
        {{
            "cta_text": "The call-to-action text",
            "action_type": "The type of action (e.g., 'comment', 'share', 'connect')",
            "urgency_level": "The level of urgency (e.g., 'high', 'medium', 'low')"
        }}"""),
        ("human", "Generate a CTA for a post about: {topic}\nContent: {content}")
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a LinkedIn content creator
- Defines what makes an effective CTA
- Provides guidance on factors to consider
- Specifies the output format
- Provides a template for the human query that includes the topic and content

### Run Method

```python
async def run(self, state: AgentState) -> AgentState:
    logger.debug(f"CTA Generator - Input State Type: {type(state)}")
    logger.debug(f"CTA Generator - Input State Content: {state}")
    
    # Convert state dictionary to AgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to AgentState")
        state = AgentState(**state)
        logger.debug(f"Converted State Type: {type(state)}")
        logger.debug(f"Converted State Content: {state}")
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic selected for CTA generation")
        
    if not state.body_text:
        logger.error("No body content found in state")
        raise ValueError("No body content available for CTA generation")
        
    prompt = self.create_prompt()
    chain = prompt | self.llm | self.parser
    
    # Get CTA text
    result = await chain.ainvoke({
        "topic": state.current_topic,
        "content": state.body_text
    })
    logger.debug(f"CTA Generation Result: {result}")
    
    # Convert result to CTAResult if it's a dictionary
    if isinstance(result, dict):
        result = CTAResult(**result)
    
    # Update state
    state.cta_text = result.cta_text
    state.messages.append({
        "role": "assistant",
        "content": f"Generated CTA: {result.cta_text}\nAction Type: {result.action_type}\nUrgency Level: {result.urgency_level}"
    })
    
    logger.debug(f"CTA Generator - Output State Type: {type(state)}")
    logger.debug(f"CTA Generator - Output State Content: {state}")
    return state
```

The run method:
1. Validates the input state has a topic and body content
2. Creates the prompt and chain
3. Invokes the LLM to generate a CTA based on topic and body content
4. Parses the structured CTA result
5. Updates the state with the CTA text and metadata
6. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("generate_cta", self.run)
    workflow.set_entry_point("generate_cta")
    workflow.add_edge("generate_cta", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for CTA generation
- An edge to the end
- Entry point set to the CTA generation node

## CTA Characteristics

The CTA Generator creates call-to-actions that:
- Clearly state what action the reader should take
- Align with the post's topic and content
- Use strong, action-oriented language
- Create a sense of value or urgency when appropriate
- Encourage engagement through comments, shares, or other LinkedIn interactions
- Are conversational and personal rather than overly promotional
- End the post on a strong note

## Common CTA Types

1. **Question CTAs**: Ask readers to share their thoughts/experiences
2. **Share CTAs**: Encourage readers to share the post with their network
3. **Connection CTAs**: Invite readers to connect with the author
4. **Resource CTAs**: Direct readers to additional resources
5. **Poll CTAs**: Ask readers to vote on options in comments
6. **Tag CTAs**: Invite readers to tag others who might benefit
7. **Follow CTAs**: Encourage readers to follow for more content

## Functionality Flow

1. **Input**: Receives a state with a selected topic and body content
2. **Processing**:
   - Creates a prompt for CTA generation using topic and body content
   - Uses the LLM to generate an appropriate CTA
   - Determines action type and urgency level
3. **Output**: Updates state with the CTA text and additional metadata

## Integration Points

The CTA Generator Agent:
- Receives input from the Body Generator Agent
- Outputs to the QA Agent
- Uses the topic and body_text fields from the AgentState
- Updates the cta_text field in the AgentState

## Example Output

```json
{
  "cta_text": "What AI tools are you currently using in your content marketing strategy? Share your experiences in the comments below, and let's learn from each other's implementations. If you're just starting your AI journey, what's your biggest question or concern? Tag a colleague who might benefit from this conversation!",
  "action_type": "comment and tag",
  "urgency_level": "medium"
}
``` 