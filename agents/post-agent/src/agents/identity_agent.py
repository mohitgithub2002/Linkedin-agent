from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError
from langgraph.graph import StateGraph, Graph
import psycopg2
from contextlib import contextmanager
import os
import re
import textstat
from dotenv import load_dotenv
from .base import BaseAgent, AgentState
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class VisualSpec(BaseModel):
    """Visual identity specifications."""
    primary_color: str = Field(pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    background: str
    font_family: str
    icon: str | None = None

class IdentitySpec(BaseModel):
    """Main style-guide spec as stored in identity_spec.spec JSONB column."""
    creator: str
    promise: str
    voice: Dict[str, Any]
    visual: VisualSpec
    pillars_ranked: list[str]
    signature_stories: list[str]
    hook_templates: list[str]
    cta_style: str

class IdentityAgentState(AgentState):
    """Extended state model for identity agent."""
    identity_spec: Optional[IdentitySpec] = Field(default=None, description="Current identity specification")
    validators: Optional[Dict[str, Any]] = Field(default=None, description="Validation functions")

class IdentityAgent(BaseAgent):
    """Agent responsible for maintaining brand identity and validation."""
    
    def __init__(self):
        super().__init__(name="identity_agent")
        logger.info("Initializing IdentityAgent")
        self._setup_validators()
        
    def _setup_validators(self):
        """Initialize validation functions."""
        logger.debug("Setting up validation functions")
        self._MAX_EMOJIS = 1
        self._MAX_SENTENCE_LEN = 25
        self._EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
        logger.debug(f"Validation parameters set: MAX_EMOJIS={self._MAX_EMOJIS}, MAX_SENTENCE_LEN={self._MAX_SENTENCE_LEN}")
        
    def _get_db_connection(self):
        """Return a new DB connection using DATABASE_URL env var."""
        logger.debug("Attempting to establish database connection")
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            logger.error("DATABASE_URL environment variable not set")
            raise RuntimeError("DATABASE_URL env var not set")
        try:
            conn = psycopg2.connect(dsn, connect_timeout=5)
            logger.debug("Database connection established successfully")
            return conn
        except Exception as e:
            logger.error(f"Failed to establish database connection: {str(e)}")
            raise
        
    @contextmanager
    def _db_cursor(self):
        """Context manager for database cursor."""
        logger.debug("Creating database cursor")
        conn = self._get_db_connection()
        try:
            cur = conn.cursor()
            logger.debug("Database cursor created successfully")
            yield cur
        except Exception as e:
            logger.error(f"Error with database cursor: {str(e)}")
            raise
        finally:
            logger.debug("Closing database cursor and connection")
            cur.close()
            conn.close()
            
    def _validate_hook(self, hook: str, hook_templates: list[str]) -> Tuple[bool, str | None]:
        """Check if hook matches at least one approved template pattern."""
        logger.debug(f"Validating hook against {len(hook_templates)} templates")
        logger.debug(f"Hook to validate: {hook}")
        
        for i, tmpl in enumerate(hook_templates):
            logger.debug(f"Checking template {i+1}: {tmpl}")
            pattern = re.escape(tmpl).replace(r"\{", "{").replace(r"\}", "}")
            pattern = re.sub(r"\{[^}]+\}", ".+", pattern)
            logger.debug(f"Generated pattern: {pattern}")
            
            if re.fullmatch(pattern, hook):
                logger.info(f"Hook matched template {i+1}")
                return True, None
                
        logger.warning("Hook did not match any approved templates")
        return False, "Hook does not match any approved template"
        
    def _score_tone(self, text: str) -> float:
        """Return a rough 0-1 readability/energy score (higher is better)."""
        logger.debug("Calculating tone score")
        reading_grade = textstat.flesch_kincaid_grade(text)
        logger.debug(f"Reading grade: {reading_grade}")
        
        if reading_grade <= 5:
            score = 1.0
        elif reading_grade >= 14:
            score = 0.2
        else:
            score = max(0.2, 1.0 - (reading_grade - 5) * 0.05)
            
        logger.debug(f"Calculated tone score: {score}")
        return score
        
    def _validate_body(self, text: str) -> Tuple[bool, str | None]:
        """Validate body text against identity rules."""
        logger.debug("Validating body text")
        sentences = re.split(r"[.!?]", text)
        long_sentences = [s for s in sentences if len(s.split()) > self._MAX_SENTENCE_LEN]
        emoji_count = len(self._EMOJI_RE.findall(text))
        
        logger.debug(f"Found {len(long_sentences)} long sentences and {emoji_count} emojis")
        
        if long_sentences:
            logger.warning(f"Found {len(long_sentences)} sentences exceeding maximum length")
            return False, "Sentence too long"
        if emoji_count > self._MAX_EMOJIS:
            logger.warning(f"Found {emoji_count} emojis, exceeding maximum of {self._MAX_EMOJIS}")
            return False, "Too many emojis"
            
        logger.info("Body text validation passed")
        return True, None
        
    async def run(self, state: IdentityAgentState) -> IdentityAgentState:
        """Run the identity agent's main logic."""
        logger.info("Starting identity agent run")
        try:
            with self._db_cursor() as cur:
                # Fetch current identity spec
                logger.debug("Fetching current identity specification")
                cur.execute("""
                    SELECT id, spec
                    FROM identity_spec
                    WHERE valid_to IS NULL
                    ORDER BY valid_from DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                
                if row is None:
                    logger.error("No active identity specification found in database")
                    raise RuntimeError("No active identity spec found")
                    
                identity_id, spec_json = row
                logger.info(f"Found identity specification with ID: {identity_id}")
                logger.debug(f"Raw specification: {spec_json}")
                
                try:
                    identity_spec = IdentitySpec.model_validate(spec_json)
                    logger.info(f"Successfully validated identity specification for creator: {identity_spec}")
                    logger.debug(f"Identity specification details: {identity_spec}")
                except ValidationError as e:
                    logger.error(f"Identity specification validation failed: {str(e)}")
                    raise RuntimeError(f"Identity spec validation failed: {e}")
                    
            # Build validators dict
            logger.debug("Building validation functions")
            validators = {
                "hook": lambda h: self._validate_hook(h, identity_spec.hook_templates),
                "tone": self._score_tone,
                "body": self._validate_body,
            }
            
            # Update state
            logger.debug("Updating agent state")
            state.identity_spec = identity_spec
            state.validators = validators
            
            # Add identity info to messages
            state.messages.append({
                "role": "system",
                "content": f"Identity loaded for creator: {identity_spec.creator}"
            })
            
            logger.info("Identity agent run completed successfully")
            return state
            
        except Exception as e:
            logger.error(f"Identity agent error: {str(e)}", exc_info=True)
            state.messages.append({
                "role": "error",
                "content": f"Identity agent error: {str(e)}"
            })
            raise
            
    def get_graph(self) -> Graph:
        """Get the agent's workflow graph."""
        logger.debug("Creating workflow graph")
        workflow = StateGraph(IdentityAgentState)
        workflow.add_node("identity", self.run)
        workflow.set_entry_point("identity")
        logger.debug("Workflow graph created successfully")
        return workflow.compile() 