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
def create_prompt(self, identity_spec: Any) -> ChatPromptTemplate:
    # Convert complex objects to simple strings to avoid formatting issues
    voice_str = str(identity_spec.voice).replace("{", "{{").replace("}", "}}")
    pillars_str = str(identity_spec.pillars_ranked).replace("{", "{{").replace("}", "}}")
    stories_str = str(identity_spec.signature_stories).replace("{", "{{").replace("}", "}}")
    
    # Create a simple system message with no JSON example
    system_message = f"""You are a professional LinkedIn content creator for {identity_spec.creator}. 

Your task is to create engaging body content for a LinkedIn post that:
1. Aligns with the creator's brand identity
2. Flows naturally from the hook
3. Includes relevant research and insights
4. Maintains the creator's voice and tone: {voice_str}
5. Incorporates the creator's brand pillars: {pillars_str}
6. Supports the creator's promise: {identity_spec.promise}

Consider these elements:
- The hook and its tone to ensure smooth transition
- The topic and its context
- Research data and insights
- Target audience
- Professional value
- Creator's signature stories: {stories_str}

Output a JSON with these fields:
- body_text: The main content as a string
- key_points: A list of key points covered in the body
- tone: A SINGLE word or phrase describing the tone (e.g. "professional" or "conversational"), not a list"""

    # Create a completely separate human message template
    human_message = "Generate body content for a post about: {topic}\nHook: {hook}\nResearch Context:\n{research}"
    
    # Create template with simple parts
    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message)
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a creator-specific LinkedIn content creator
- Incorporates brand identity specifications from the identity agent
- Provides the creator's voice guidelines, brand pillars, and promise
- Integrates the creator's signature stories for consistent storytelling
- Instructs on alignment with the creator's overall brand identity
- Properly escapes complex objects to avoid template formatting issues
- Specifies the output format with clear guidance on tone formatting

### Run Method

```python
async def run(self, state: IdentityAgentState) -> IdentityAgentState:
    logger.debug(f"Body Generator - Input State Type: {type(state)}")
    logger.debug(f"Body Generator - Input State Content: {state}")
    
    # Convert state dictionary to IdentityAgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to IdentityAgentState")
        state = IdentityAgentState(**state)
    
    # Save initial checkpoint
    self.save_checkpoint(state)
        
    # Validate input state
    if not state.current_topic:
        raise ValueError("No topic provided in state")
        
    if not state.hook_text:
        raise ValueError("No hook provided in state")
        
    if not state.identity_spec:
        raise ValueError("Identity specification required for body generation")
        
    # Create prompt
    prompt = self.create_prompt(state.identity_spec)
    chain = prompt | self.llm | self.parser
    
    try:
        # Prepare research context
        research_context = "\n".join([
            f"{item['source']}: {item['snippet']}"
            for item in state.research_data
        ]) if state.research_data else "No research data available"
        
        # Invoke the chain
        result = await chain.ainvoke({
            "topic": state.current_topic,
            "hook": state.hook_text,
            "research": research_context
        })
        
        # Handle case where tone might be a list instead of a string
        if isinstance(result, dict) and "tone" in result and isinstance(result["tone"], list):
            logger.warning(f"Tone returned as a list: {result['tone']}. Converting to string.")
            result["tone"] = ", ".join(result["tone"])
        
        # Convert result to BodyResult if it's a dictionary
        if isinstance(result, dict):
            result = BodyResult(**result)
        elif not isinstance(result, BodyResult):
            raise ValueError(f"Unexpected result type: {type(result)}")
            
        # Validate body against identity rules
        if state.validators and "body" in state.validators:
            is_valid, error_msg = state.validators["body"](result.body_text)
            if not is_valid:
                logger.warning(f"Body validation failed: {error_msg}")
                # Retry with more specific guidance
                prompt = self.create_prompt(state.identity_spec)
                chain = prompt | self.llm | self.parser
                retry_result = await chain.ainvoke({
                    "topic": state.current_topic,
                    "hook": state.hook_text,
                    "research": research_context,
                    "error": f"Previous body failed validation: {error_msg}. Please try again."
                })
                
                # Handle case where tone might be a list in retry
                if isinstance(retry_result, dict) and "tone" in retry_result and isinstance(retry_result["tone"], list):
                    logger.warning(f"Tone returned as a list in retry: {retry_result['tone']}. Converting to string.")
                    retry_result["tone"] = ", ".join(retry_result["tone"])
                    
                if isinstance(retry_result, dict):
                    result = BodyResult(**retry_result)
                    
        # Score tone if validator available
        if state.validators and "tone" in state.validators:
            tone_score = state.validators["tone"](result.body_text)
            logger.info(f"Body tone score: {tone_score}")
            if tone_score < 0.6:  # Threshold for acceptable tone
                logger.warning("Body tone score too low, regenerating")
                prompt = self.create_prompt(state.identity_spec)
                chain = prompt | self.llm | self.parser
                retry_result = await chain.ainvoke({
                    "topic": state.current_topic,
                    "hook": state.hook_text,
                    "research": research_context,
                    "error": "Previous body tone score was too low. Please improve readability and engagement."
                })
                
                # Handle case where tone might be a list in retry
                if isinstance(retry_result, dict) and "tone" in retry_result and isinstance(retry_result["tone"], list):
                    logger.warning(f"Tone returned as a list in tone retry: {retry_result['tone']}. Converting to string.")
                    retry_result["tone"] = ", ".join(retry_result["tone"])
                    
                if isinstance(retry_result, dict):
                    result = BodyResult(**retry_result)
        
        # Update state
        state.body_text = result.body_text
        state.messages.append({
            "role": "assistant",
            "content": f"Generated body text: {result.body_text}"
        })
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
    except Exception as e:
        logger.error(f"Error in BodyGeneratorAgent: {str(e)}", exc_info=True)
        raise
    
    return state
```

The run method:
1. Validates the input state has a topic, hook, and identity specification
2. Creates the prompt with the identity specification
3. Prepares the research context from research data
4. Invokes the LLM to generate body content
5. Handles potential format issues (like tone being returned as a list)
6. Validates the body against identity rules from the validators
7. Retries body generation with specific guidance if validation fails
8. Scores the tone using the identity validator and regenerates if below threshold
9. Updates the state with the body text
10. Saves checkpoints for progress tracking
11. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(IdentityAgentState)
    workflow.add_node("generate_body", self.run)
    workflow.set_entry_point("generate_body")
    workflow.add_edge("generate_body", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for body generation
- An edge to the end
- Entry point set to the body generation node
- Using IdentityAgentState for state management

## Content Validation

The body generator uses two types of identity-based validation:

1. **Content Rules Validation**:
   - Checks sentence length against maximum allowed
   - Validates emoji usage against maximum allowed
   - Ensures content meets creator brand standards
   - Regenerates content if validation fails

2. **Tone Scoring**:
   - Uses the Flesch-Kincaid readability scoring
   - Evaluates readability on a 0-1 scale (higher is better)
   - Sets a threshold (0.6) for acceptable content
   - Regenerates content if tone score is too low

## Functionality Flow

1. **Input**: Receives a state with identity specifications, validators, hook text, and research data
2. **Processing**:
   - Creates a prompt with creator-specific identity elements
   - Formats research data into a usable context
   - Generates body content aligned with brand identity
   - Validates content against identity rules
   - Scores tone for readability and engagement
   - Regenerates if validation fails or tone score is low
3. **Output**: Updates state with the validated body text and metadata

## Integration Points

The Body Generator Agent:
- Receives input from the Hook Generator Agent
- Uses identity specifications from the Identity Agent
- Applies validation rules from the Identity Agent
- Outputs to the CTA Generator Agent
- Updates the body_text field in the IdentityAgentState

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