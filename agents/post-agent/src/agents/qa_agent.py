from typing import Any, Dict, List
from .base import BaseAgent, AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import Graph, StateGraph
import logging

logger = logging.getLogger(__name__)

class QAResult(BaseModel):
    feedback: str = Field(description="The feedback on the post's quality and effectiveness")
    suggestions: List[str] = Field(description="List of suggestions for improvement")
    score: int = Field(description="Quality score from 1-10")
    issues: List[str] = Field(description="List of identified issues or concerns")

class QAAgent(BaseAgent):
    """Agent responsible for quality assurance and feedback on LinkedIn posts."""
    
    def __init__(self):
        super().__init__("qa_agent")
        self.parser = JsonOutputParser(pydantic_object=QAResult)
        
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
    
    async def run(self, state: AgentState) -> AgentState:
        logger.debug(f"QA Agent - Input State Type: {type(state)}")
        logger.debug(f"QA Agent - Input State Content: {state}")
        
        # Convert state dictionary to AgentState if needed
        if isinstance(state, dict):
            logger.info("Converting dictionary state to AgentState")
            state = AgentState(**state)
            logger.debug(f"Converted State Type: {type(state)}")
            logger.debug(f"Converted State Content: {state}")
            
        # Save initial checkpoint
        self.save_checkpoint(state)
            
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
        
        # Save final checkpoint
        self.save_checkpoint(state)
        
        logger.debug(f"QA Agent - Output State Type: {type(state)}")
        logger.debug(f"QA Agent - Output State Content: {state}")
        return state
    
    def get_graph(self) -> Graph:
        workflow = StateGraph(AgentState)
        workflow.add_node("qa_check", self.run)
        workflow.set_entry_point("qa_check")
        workflow.add_edge("qa_check", "end")
        return workflow.compile() 