# QA Agent Documentation (qa_agent.py)

## Overview

The `QAAgent` is the sixth agent in the LinkedIn post generation workflow. It is responsible for quality assurance, reviewing the generated content for effectiveness, engagement potential, coherence, and adherence to professional standards. This agent adds a critical evaluation layer before final assembly, ensuring the post meets quality benchmarks.

## Data Models

### QAResult Model

```python
class QAResult(BaseModel):
    feedback: str = Field(description="The feedback on the post's quality and effectiveness")
    suggestions: List[str] = Field(description="List of suggestions for improvement")
    score: int = Field(description="Quality score from 1-10")
    issues: List[str] = Field(description="List of identified issues or concerns")
```

This model represents the QA evaluation with:
- Overall feedback on the post's quality
- Specific suggestions for improvement
- A numerical quality score (1-10)
- A list of identified issues or concerns

## Agent Implementation

```python
class QAAgent(BaseAgent):
    """Agent responsible for quality assurance and feedback on LinkedIn posts."""
    
    def __init__(self):
        super().__init__("qa_agent")
        self.parser = JsonOutputParser(pydantic_object=QAResult)
```

The constructor initializes the agent with:
- Base agent configuration with name "qa_agent"
- JSON output parser configured for the QAResult model

### Prompt Creation

```python
def create_prompt(self) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are a professional LinkedIn content quality assurance expert. Your task is to:
        1. Review the post for quality and effectiveness
        2. Identify any issues or areas for improvement
        3. Provide constructive feedback
        4. Score the overall quality
        
        Consider:
        - Content clarity and structure
        - Engagement potential
        - Professional tone
        - Grammar and readability
        - Value to the target audience
        
        Format your response as a JSON object with the following structure:
        {{
            "feedback": "Overall feedback on the post",
            "suggestions": ["Suggestion 1", "Suggestion 2", ...],
            "score": 7,
            "issues": ["Issue 1", "Issue 2", ...]
        }}"""),
        ("human", """Review the following LinkedIn post:
        Topic: {topic}
        Hook: {hook}
        Body: {body}
        CTA: {cta}""")
    ])
```

Creates a prompt for the agent that:
- Establishes the role as a LinkedIn content QA expert
- Defines the evaluation criteria
- Provides guidance on factors to consider
- Specifies the output format
- Provides a template for the human query that includes all post components

### Run Method

```python
async def run(self, state: AgentState) -> AgentState:
    logger.debug(f"QA Agent - Input State Type: {type(state)}")
    logger.debug(f"QA Agent - Input State Content: {state}")
    
    # Convert state dictionary to AgentState if needed
    if isinstance(state, dict):
        logger.info("Converting dictionary state to AgentState")
        state = AgentState(**state)
        logger.debug(f"Converted State Type: {type(state)}")
        logger.debug(f"Converted State Content: {state}")
        
    if not state.current_topic:
        logger.error("No topic found in state")
        raise ValueError("No topic available for QA review")
        
    if not state.hook_text:
        logger.error("No hook found in state")
        raise ValueError("No hook available for QA review")
        
    if not state.body_text:
        logger.error("No body content found in state")
        raise ValueError("No body content available for QA review")
        
    if not state.cta_text:
        logger.error("No CTA found in state")
        raise ValueError("No CTA available for QA review")
        
    prompt = self.create_prompt()
    chain = prompt | self.llm | self.parser
    
    # Get QA feedback
    result = await chain.ainvoke({
        "topic": state.current_topic,
        "hook": state.hook_text,
        "body": state.body_text,
        "cta": state.cta_text
    })
    logger.debug(f"QA Review Result: {result}")
    
    # Convert result to QAResult if it's a dictionary
    if isinstance(result, dict):
        result = QAResult(**result)
    
    # Update state
    state.qa_feedback = result.feedback
    state.qa_suggestions = result.suggestions
    state.qa_score = result.score
    state.qa_issues = result.issues
    
    state.messages.append({
        "role": "assistant",
        "content": f"QA Review:\nScore: {result.score}/10\nFeedback: {result.feedback}\nSuggestions: {', '.join(result.suggestions)}\nIssues: {', '.join(result.issues)}"
    })
    
    logger.debug(f"QA Agent - Output State Type: {type(state)}")
    logger.debug(f"QA Agent - Output State Content: {state}")
    return state
```

The run method:
1. Validates the input state has all necessary post components
2. Creates the prompt and chain
3. Invokes the LLM to evaluate the complete post
4. Parses the structured QA result
5. Updates the state with the feedback, suggestions, score, and issues
6. Returns the updated state

### Graph Method

```python
def get_graph(self) -> Graph:
    workflow = StateGraph(AgentState)
    workflow.add_node("qa_check", self.run)
    workflow.set_entry_point("qa_check")
    workflow.add_edge("qa_check", "end")
    return workflow.compile()
```

Creates a simple LangGraph workflow with:
- A single node for QA evaluation
- An edge to the end
- Entry point set to the QA check node

## Quality Assessment Criteria

The QA Agent evaluates posts based on:

1. **Content Quality**
   - Accuracy and credibility of information
   - Depth and value of insights
   - Originality and differentiation

2. **Engagement Potential**
   - Hook effectiveness
   - Overall interest level
   - Call-to-action strength

3. **Writing Quality**
   - Grammar and spelling
   - Clarity and conciseness
   - Flow and structure

4. **Professional Standards**
   - Appropriate tone for LinkedIn
   - Target audience alignment
   - Professional language

5. **Technical Aspects**
   - Post length (optimal for LinkedIn)
   - Formatting appropriateness
   - Readability

## Functionality Flow

1. **Input**: Receives a state with all post components (topic, hook, body, CTA)
2. **Processing**:
   - Creates a prompt for QA review of the complete post
   - Uses the LLM to evaluate overall quality
   - Generates specific feedback and suggestions
   - Assigns a numerical quality score
   - Identifies any issues requiring attention
3. **Output**: Updates state with QA feedback, suggestions, score, and issues

## Integration Points

The QA Agent:
- Receives input from the CTA Generator Agent
- Outputs to the Final Assembler Agent
- Uses all content fields from the AgentState
- Updates the qa_feedback, qa_suggestions, qa_score, and qa_issues fields

## Example Output

```json
{
  "feedback": "This post presents a strong, data-backed overview of AI in content marketing with a clear structure and professional tone. The hook effectively uses statistics to grab attention, and the body develops key points logically with good supporting evidence. The CTA encourages meaningful engagement through questions and community building.",
  "suggestions": [
    "Consider adding one specific example of an AI tool to make the content more actionable",
    "The body could benefit from one short sentence highlighting potential challenges of AI adoption",
    "Add one or two relevant LinkedIn hashtags at the very end to increase discoverability"
  ],
  "score": 8,
  "issues": [
    "The post is on the longer side for LinkedIn - consider tightening some sentences",
    "The transition between the body and CTA could be smoother"
  ]
}
``` 