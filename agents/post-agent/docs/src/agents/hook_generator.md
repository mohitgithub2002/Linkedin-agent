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
    
    return template
```

Creates a prompt for the agent that:
- Establishes the role as a creator-specific LinkedIn content creator
- Incorporates brand identity specifications from the identity agent
- Provides the creator's voice guidelines, brand pillars, and promise
- Uses the creator's approved hook templates
- Specifies the output format
- Properly escapes complex objects to avoid template formatting issues

### Run Method

```python
async def run(self, state: IdentityAgentState) -> IdentityAgentState:
    logger.debug(f"Hook Generator - Input State Type: {type(state)}")
    logger.debug(f"Hook Generator - Input State Content: {state}")
    
    # Convert state dictionary to IdentityAgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to IdentityAgentState")
        state = IdentityAgentState(**state)
    
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
    chain = prompt | self.llm | self.parser
    
    # Get hook text with only the topic variable
    try:
        result = await chain.ainvoke({"topic": state.current_topic})
        
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
    
    return state
```

The run method:
1. Validates the input state has a topic and identity specification
2. Creates the prompt with the identity specification
3. Invokes the LLM to generate a hook
4. Handles potential format issues (like tone being returned as a list)
5. Validates the hook against identity rules from the validators
6. Retries hook generation with specific guidance if validation fails
7. Updates the state with the hook text and metadata
8. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(IdentityAgentState)
    workflow.add_node("generate_hook", self.run)
    workflow.set_entry_point("generate_hook")
    workflow.add_edge("generate_hook", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for hook generation
- An edge to the end
- Entry point set to the hook generation node
- Using IdentityAgentState for state management

## Functionality Flow

1. **Input**: Receives a state with identity specifications, validators, and a selected topic
2. **Processing**:
   - Creates a prompt for hook generation based on the identity spec and topic
   - Uses the LLM to generate an engaging hook
   - Validates the hook against identity-specified templates
   - Retries if the hook fails validation
   - Determines appropriate tone and target audience
3. **Output**: Updates state with the validated hook text and additional metadata

## Hook Validation

The hook generator utilizes the identity agent's validators to ensure:
1. The hook follows one of the approved hook templates
2. The content aligns with the creator's brand voice
3. The format meets established standards

If validation fails, the agent:
1. Logs the validation error
2. Creates a new prompt with the specific validation error
3. Attempts regeneration with more specific guidance
4. Validates the new hook before finalizing

## Integration Points

The Hook Generator Agent:
- Receives input from the Research Agent
- Uses identity specifications from the Identity Agent
- Applies validation rules from the Identity Agent
- Outputs to the Body Generator Agent
- Updates the hook_text field in the IdentityAgentState

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