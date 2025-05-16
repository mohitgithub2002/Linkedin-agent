# Identity Agent Documentation (identity_agent.py)

## Overview

The `IdentityAgent` is the first agent in the LinkedIn post generation workflow. It is responsible for loading and enforcing brand identity guidelines throughout the content creation process. This agent acts as a gatekeeper, ensuring all generated content adheres to the creator's brand voice, style, and validation rules.

## Data Models

### VisualSpec Model

```python
class VisualSpec(BaseModel):
    """Visual identity specifications."""
    primary_color: str = Field(pattern=r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    background: str
    font_family: str
    icon: str | None = None
```

Defines visual brand identity elements:
- Primary color (as a hex code)
- Background specification
- Font family
- Optional icon identifier

### IdentitySpec Model

```python
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
```

Contains the complete brand identity specification:
- Creator name
- Brand promise
- Voice characteristics
- Visual identity (as a VisualSpec)
- Ranked brand pillars
- Signature stories
- Approved hook templates
- CTA style guidelines

### IdentityAgentState Model

```python
class IdentityAgentState(AgentState):
    """Extended state model for identity agent."""
    identity_spec: Optional[IdentitySpec] = Field(default=None, description="Current identity specification")
    validators: Optional[Dict[str, Any]] = Field(default=None, description="Validation functions")
```

Extends the base AgentState to include:
- The identity specification
- Validation functions for content quality assurance

## Agent Implementation

```python
class IdentityAgent(BaseAgent):
    """Agent responsible for maintaining brand identity and validation."""
    
    def __init__(self):
        super().__init__(name="identity_agent")
        logger.info("Initializing IdentityAgent")
        self._setup_validators()
```

The constructor initializes the agent with:
- Base agent configuration with name "identity_agent"
- Setup for content validation functions

### Validator Setup

```python
def _setup_validators(self):
    """Initialize validation functions."""
    logger.debug("Setting up validation functions")
    self._MAX_EMOJIS = 1
    self._MAX_SENTENCE_LEN = 25
    self._EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
```

Configures content validation parameters:
- Maximum number of emojis allowed (1)
- Maximum sentence length (25 words)
- Regular expression for emoji detection

### Database Integration

```python
def _get_db_connection(self):
    """Return a new DB connection using DATABASE_URL env var."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL env var not set")
    conn = psycopg2.connect(dsn, connect_timeout=5)
    return conn
    
@contextmanager
def _db_cursor(self):
    """Context manager for database cursor."""
    conn = self._get_db_connection()
    try:
        cur = conn.cursor()
        yield cur
    finally:
        cur.close()
        conn.close()
```

Handles database connections:
- Retrieves database connection string from environment variables
- Creates and manages database connections and cursors
- Provides proper resource cleanup

### Content Validation Methods

```python
def _validate_hook(self, hook: str, hook_templates: list[str]) -> Tuple[bool, str | None]:
    """Check if hook matches at least one approved template pattern."""
    for tmpl in hook_templates:
        pattern = re.escape(tmpl).replace(r"\{", "{").replace(r"\}", "}")
        pattern = re.sub(r"\{[^}]+\}", ".+", pattern)
        if re.fullmatch(pattern, hook):
            return True, None
    return False, "Hook does not match any approved template"
    
def _score_tone(self, text: str) -> float:
    """Return a rough 0-1 readability/energy score (higher is better)."""
    reading_grade = textstat.flesch_kincaid_grade(text)
    if reading_grade <= 5:
        score = 1.0
    elif reading_grade >= 14:
        score = 0.2
    else:
        score = max(0.2, 1.0 - (reading_grade - 5) * 0.05)
    return score
    
def _validate_body(self, text: str) -> Tuple[bool, str | None]:
    """Validate body text against identity rules."""
    sentences = re.split(r"[.!?]", text)
    long_sentences = [s for s in sentences if len(s.split()) > self._MAX_SENTENCE_LEN]
    emoji_count = len(self._EMOJI_RE.findall(text))
    
    if long_sentences:
        return False, "Sentence too long"
    if emoji_count > self._MAX_EMOJIS:
        return False, "Too many emojis"
    return True, None
```

Implements content validation logic:
- **Hook validation**: Ensures hooks follow approved templates
- **Tone scoring**: Evaluates readability and engagement potential
- **Body validation**: Checks for sentence length and emoji usage

### Run Method

```python
async def run(self, state: IdentityAgentState) -> IdentityAgentState:
    """Run the identity agent's main logic."""
    try:
        with self._db_cursor() as cur:
            # Fetch current identity spec
            cur.execute("""
                SELECT id, spec
                FROM identity_spec
                WHERE valid_to IS NULL
                ORDER BY valid_from DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            
            if row is None:
                raise RuntimeError("No active identity spec found")
                
            identity_id, spec_json = row
            
            try:
                identity_spec = IdentitySpec.model_validate(spec_json)
            except ValidationError as e:
                raise RuntimeError(f"Identity spec validation failed: {e}")
                
        # Build validators dict
        validators = {
            "hook": lambda h: self._validate_hook(h, identity_spec.hook_templates),
            "tone": self._score_tone,
            "body": self._validate_body,
        }
        
        # Update state
        state.identity_spec = identity_spec
        state.validators = validators
        
        # Add identity info to messages
        state.messages.append({
            "role": "system",
            "content": f"Identity loaded for creator: {identity_spec.creator}"
        })
        
        return state
        
    except Exception as e:
        state.messages.append({
            "role": "error",
            "content": f"Identity agent error: {str(e)}"
        })
        raise
```

The main method that:
1. Retrieves the current identity specification from the database
2. Validates the specification using Pydantic
3. Creates validator functions for content verification
4. Updates the agent state with specifications and validators
5. Adds a status message to the conversation history
6. Handles errors with appropriate logging

### Graph Method

```python
def get_graph(self) -> Graph:
    """Get the agent's workflow graph."""
    workflow = StateGraph(IdentityAgentState)
    workflow.add_node("identity", self.run)
    workflow.set_entry_point("identity")
    return workflow.compile()
```

Creates a LangGraph workflow with:
- A single node for identity loading
- Entry point set to the identity node

## Functionality Flow

1. **Initialization**: Set up validation parameters and rules
2. **Database Load**: Retrieve the current identity specification from PostgreSQL
3. **Validation Setup**: Create validator functions for content checking
4. **State Update**: Add identity information to the agent state
5. **Result**: Return the updated state for the next agent in the workflow

## Integration with Other Agents

The Identity Agent provides critical services to other agents:
- **Hook Generator**: Uses hook templates and validators to create compliant hooks
- **Body Generator**: Uses style guidelines and validators for content generation
- **CTA Generator**: Follows CTA style guidelines from identity spec
- **All Agents**: Access creator-specific information to maintain consistent voice and branding

## Database Schema

The identity agent relies on a database table with this structure:

```sql
CREATE TABLE identity_spec (
    id SERIAL PRIMARY KEY,
    creator_id INTEGER NOT NULL,
    spec JSONB NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE
);
```

Key fields:
- **id**: Unique identifier for the specification
- **creator_id**: Reference to the content creator
- **spec**: JSONB field containing the full identity specification
- **valid_from/valid_to**: Versioning timestamps for historical tracking 