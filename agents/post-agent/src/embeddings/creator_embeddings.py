"""
generate_embeddings.py
Replace DATABASE_URL with your own, then run:
    python generate_embeddings.py
"""

import os
import openai
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
# ❶ CONFIG
DATABASE_URL = os.getenv("DATABASE_URL")
openai.api_key = os.getenv("OPENAI_API_KEY")
IDENTITY_ID = 1  # ← the id from step 2

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

# ❷ Get embeddings from OpenAI
response = openai.embeddings.create(
    model="text-embedding-ada-002",
    input=phrases,
)
vectors = [item.embedding for item in response.data]

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