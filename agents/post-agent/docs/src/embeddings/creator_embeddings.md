# Creator Embeddings Documentation (creator_embeddings.py)

## Overview

The `creator_embeddings.py` script is responsible for generating and storing vector embeddings of brand-related phrases in a PostgreSQL database. These embeddings enable semantic similarity searches for content that aligns with a creator's brand identity and voice. The script uses OpenAI's embedding API to convert text phrases into high-dimensional vectors that capture semantic meaning.

## Implementation

```python
import os
import openai
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
# ❶ CONFIG
DATABASE_URL = os.getenv("DATABASE_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")
IDENTITY_ID = 1  # ← the id from identity_spec table
```

The script begins by:
- Importing necessary libraries for API access and database operations
- Loading environment variables for configuration
- Setting up connections to the database and OpenAI API
- Defining the identity ID to associate embeddings with a specific creator

### Phrase Definition

```python
phrases = [
    "conversational",
    "authoritative",
    "friendly",
    "visionary",
    "passionate",
    "Fun Startup Building",
    "Founder Mindset & Leadership",
    "AI/Automation for Scale",
    "Bootstrapping Business",
    "System-Thinking",
]
```

This section defines:
- A list of phrases that characterize the creator's brand voice and topics
- Both tone descriptors (conversational, authoritative) and content themes
- Key brand pillars that represent the creator's expertise and focus

### Embedding Generation

```python
# ❷ Get embeddings from OpenAI
response = openai.embeddings.create(
    model="text-embedding-ada-002",
    input=phrases,
)
vectors = [item.embedding for item in response.data]
```

This part:
- Makes an API call to OpenAI's embedding service
- Uses the "text-embedding-ada-002" model which produces 1536-dimensional vectors
- Extracts the embedding vectors from the API response
- Stores them in a list for database insertion

### Database Operations

```python
# ❸ Insert into Postgres
with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
    cur.execute("""
        ALTER TABLE brand_embeddings 
        ALTER COLUMN embedding TYPE vector(1536)
    """)
    
    rows = [
        (IDENTITY_ID, name, vector) for name, vector in zip(phrases, vectors)
    ]
    execute_values(
        cur,
        """
        INSERT INTO brand_embeddings (identity_id, name, embedding)
        VALUES %s
        """,
        rows,
        template="(%s, %s, %s::vector)",
    )
    conn.commit()

print("Inserted", len(rows), "embeddings.")
```

The database operations include:
- Altering the table to ensure the vector column has the correct dimension (1536)
- Creating data rows that associate each phrase with its vector and the creator's identity ID
- Using the execute_values method for efficient batch insertion
- Committing the transaction to save the data
- Printing a confirmation of the number of embeddings inserted

## Database Schema

The script interacts with the following database table:

```sql
CREATE TABLE brand_embeddings (
    id SERIAL PRIMARY KEY,
    identity_id INTEGER NOT NULL REFERENCES identity_spec(id),
    name TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

Key fields:
- **id**: Unique identifier for each embedding
- **identity_id**: Reference to the creator's identity specification
- **name**: The original phrase that was embedded
- **embedding**: The 1536-dimensional vector representation of the phrase
- **created_at**: Timestamp for when the embedding was created

## Integration with Identity Agent

The creator embeddings are used by the Identity Agent to:
1. **Find Similar Content**: Match generated content against brand pillars and voice characteristics
2. **Score Content Alignment**: Measure how well content aligns with the creator's brand
3. **Validate Content**: Ensure generated content stays true to the creator's voice and topics
4. **Filter Topics**: Select topics that align with the creator's expertise and brand focus

## Usage Instructions

To use this script:

1. Ensure the required environment variables are set:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/database
   OPENAI_API_KEY=your-openai-api-key
   ```

2. Modify the `phrases` list to include relevant brand voice descriptors and topics

3. Set the `IDENTITY_ID` to match the creator's ID in the identity_spec table

4. Run the script:
   ```
   python creator_embeddings.py
   ```

## Performance Considerations

- The script uses the OpenAI Embeddings API which has rate limits and usage costs
- For large numbers of phrases, consider implementing batching to stay within API limits
- The PostgreSQL database must have the `pgvector` extension installed for vector operations

## Future Enhancements

Potential improvements to the embeddings system include:
- Implementing incremental updates to avoid regenerating all embeddings
- Adding embedding refreshes when brand voice or pillars change
- Expanding to include embeddings of creator content samples for better matching
- Implementing periodic retraining to adapt to evolving brand voice 