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
def create_prompt(self, identity_spec: Any) -> ChatPromptTemplate:
    # Convert complex objects to simple strings to avoid formatting issues
    voice_str = str(identity_spec.voice).replace("{", "{{").replace("}", "}}")
    pillars_str = str(identity_spec.pillars_ranked).replace("{", "{{").replace("}", "}}")
    cta_style = str(identity_spec.cta_style).replace("{", "{{").replace("}", "}}")
    
    # Create a simple system message with no JSON example
    system_message = f"""You are a professional LinkedIn content creator for {identity_spec.creator}. 

Your task is to create an engaging call-to-action (CTA) for a LinkedIn post that:
1. Aligns with the creator's brand identity
2. Corresponds with the post's content and tone
3. Is clear, actionable, and compelling
4. Follows the creator's CTA style: {cta_style}
5. Maintains the creator's voice: {voice_str}

Consider these elements:
- The post's main topic and content
- The target audience
- The desired action
- The tone of the post
- The creator's brand pillars: {pillars_str}
- The creator's promise: {identity_spec.promise}

Output a JSON with these fields:
- cta_text: The call-to-action text as a string
- action_type: A SINGLE word or phrase describing the action type (e.g. "comment", "share"), not a list
- urgency_level: A SINGLE word describing the urgency level (e.g. "high", "medium", "low"), not a list"""

    # Create a completely separate human message template
    human_message = "Generate a CTA for a post about: {topic}\nContent: {content}"
    
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
- Specifies adherence to the creator's defined CTA style
- Provides the creator's voice guidelines and brand pillars
- References the creator's brand promise for alignment
- Properly escapes complex objects to avoid template formatting issues
- Specifies the output format with clear guidance on field formatting

### Run Method

```python
async def run(self, state: IdentityAgentState) -> IdentityAgentState:
    logger.debug(f"CTA Generator - Input State Type: {type(state)}")
    logger.debug(f"CTA Generator - Input State Content: {state}")
    
    # Convert state dictionary to IdentityAgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to IdentityAgentState")
        state = IdentityAgentState(**state)
        
    # Save initial checkpoint
    self.save_checkpoint(state)
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic selected for CTA generation")
        
    if not state.body_text:
        logger.error("No body content found in state")
        raise ValueError("No body content available for CTA generation")
        
    if not state.identity_spec:
        logger.error("No identity spec found in state")
        raise ValueError("Identity specification required for CTA generation")
        
    # Create prompt
    prompt = self.create_prompt(state.identity_spec)
    chain = prompt | self.llm | self.parser
    
    try:
        # Get CTA text
        result = await chain.ainvoke({
            "topic": state.current_topic,
            "content": state.body_text
        })
        
        # Handle case where fields might be lists instead of strings
        if isinstance(result, dict):
            for field in ["action_type", "urgency_level", "cta_text"]:
                if field in result and isinstance(result[field], list):
                    logger.warning(f"{field} returned as a list: {result[field]}. Converting to string.")
                    result[field] = ", ".join(result[field])
        
        # Convert result to CTAResult if it's a dictionary
        if isinstance(result, dict):
            result = CTAResult(**result)
            
        # Validate CTA against identity rules
        if state.validators and "body" in state.validators:  # Reuse body validator for CTA
            is_valid, error_msg = state.validators["body"](result.cta_text)
            if not is_valid:
                logger.warning(f"CTA validation failed: {error_msg}")
                # Retry with more specific guidance
                prompt = self.create_prompt(state.identity_spec)
                chain = prompt | self.llm | self.parser
                retry_result = await chain.ainvoke({
                    "topic": state.current_topic,
                    "content": state.body_text,
                    "error": f"Previous CTA failed validation: {error_msg}. Please try again."
                })
                
                # Handle case where fields might be lists in retry
                if isinstance(retry_result, dict):
                    for field in ["action_type", "urgency_level", "cta_text"]:
                        if field in retry_result and isinstance(retry_result[field], list):
                            logger.warning(f"{field} returned as a list in retry: {retry_result[field]}. Converting to string.")
                            retry_result[field] = ", ".join(retry_result[field])
                    
                    result = CTAResult(**retry_result)
                    
        # Score tone if validator available
        if state.validators and "tone" in state.validators:
            tone_score = state.validators["tone"](result.cta_text)
            logger.info(f"CTA tone score: {tone_score}")
            if tone_score < 0.6:  # Threshold for acceptable tone
                logger.warning("CTA tone score too low, regenerating")
                prompt = self.create_prompt(state.identity_spec)
                chain = prompt | self.llm | self.parser
                retry_result = await chain.ainvoke({
                    "topic": state.current_topic,
                    "content": state.body_text,
                    "error": "Previous CTA tone score was too low. Please improve readability and engagement."
                })
                
                # Handle case where fields might be lists in tone retry
                if isinstance(retry_result, dict):
                    for field in ["action_type", "urgency_level", "cta_text"]:
                        if field in retry_result and isinstance(retry_result[field], list):
                            logger.warning(f"{field} returned as a list in tone retry: {retry_result[field]}. Converting to string.")
                            retry_result[field] = ", ".join(retry_result[field])
                    
                    result = CTAResult(**retry_result)
        
        # Update state
        state.cta_text = result.cta_text
        state.messages.append({
            "role": "assistant",
            "content": f"Generated CTA: {result.cta_text}\nAction Type: {result.action_type}\nUrgency Level: {result.urgency_level}"
        })
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
    except Exception as e:
        logger.error(f"Error in CTAGeneratorAgent: {str(e)}", exc_info=True)
        raise
    
    return state
```

The run method:
1. Validates the input state has a topic, body text, and identity specification
2. Creates the prompt with the identity specification
3. Invokes the LLM to generate a CTA based on topic and body content
4. Handles potential format issues (like fields being returned as lists)
5. Validates the CTA against identity rules from the validators
6. Retries CTA generation with specific guidance if validation fails
7. Scores the tone using the identity validator and regenerates if below threshold
8. Updates the state with the CTA text and metadata
9. Saves checkpoints for progress tracking
10. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(IdentityAgentState)
    workflow.add_node("generate_cta", self.run)
    workflow.set_entry_point("generate_cta")
    workflow.add_edge("generate_cta", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for CTA generation
- An edge to the end
- Entry point set to the CTA generation node
- Using IdentityAgentState for state management

## CTA Style Adherence

The CTA generator adheres to the creator's specific CTA style as defined in the identity specification:

1. **Style Compliance**:
   - Follows the creator's preferred CTA style (conversational, direct, question-based, etc.)
   - Maintains consistent brand voice in closing
   - Uses appropriate engagement prompts per creator guidelines

2. **Content Validation**:
   - Checks sentence length against maximum allowed
   - Validates emoji usage against maximum allowed
   - Ensures content meets creator brand standards
   - Regenerates content if validation fails

3. **Tone Scoring**:
   - Uses the Flesch-Kincaid readability scoring
   - Evaluates readability on a 0-1 scale (higher is better)
   - Sets a threshold (0.6) for acceptable content
   - Regenerates content if tone score is too low

## Functionality Flow

1. **Input**: Receives a state with identity specifications, validators, a topic, and body content
2. **Processing**:
   - Creates a prompt with creator-specific CTA style and identity elements
   - Generates a CTA aligned with brand identity and the specified style
   - Validates content against identity rules
   - Scores tone for readability and engagement
   - Regenerates if validation fails or tone score is low
3. **Output**: Updates state with the validated CTA text and metadata

## Integration Points

The CTA Generator Agent:
- Receives input from the Body Generator Agent
- Uses identity specifications from the Identity Agent
- Applies validation rules from the Identity Agent
- Outputs to the QA Agent
- Updates the cta_text field in the IdentityAgentState

## Example Output

```json
{
  "cta_text": "What AI tools are you currently using in your content marketing strategy? Share your experiences in the comments below, and let's learn from each other's implementations. If you're just starting your AI journey, what's your biggest question or concern? Tag a colleague who might benefit from this conversation!",
  "action_type": "comment and tag",
  "urgency_level": "medium"
}
``` 