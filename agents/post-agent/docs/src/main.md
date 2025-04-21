# API Layer Documentation (main.py)

## Overview

The `main.py` file implements the API layer for the LinkedIn post generation system. It uses FastAPI to create a RESTful endpoint that clients can use to request post generation.

## File Structure

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from .orchestrator import generate_post

app = FastAPI(title="LinkedIn Post Generation System")

class PostRequest(BaseModel):
    """Request model for post generation."""
    topic: Optional[str] = None
    custom_prompt: Optional[str] = None

class PostResponse(BaseModel):
    """Response model for generated post."""
    text: str
    image_url: Optional[str] = None
    status: str

@app.post("/generate-post", response_model=PostResponse)
async def create_post(request: PostRequest) -> PostResponse:
    """Generate a LinkedIn post."""
    try:
        result = await generate_post(topic=request.topic)
        
        return PostResponse(
            text=result["text"],
            image_url=result.get("image_url"),
            status="success"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating post: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
```

## Components

### FastAPI Application

```python
app = FastAPI(title="LinkedIn Post Generation System")
```

The application is initialized with FastAPI, providing a title that will appear in the auto-generated API documentation.

### Data Models

#### PostRequest

```python
class PostRequest(BaseModel):
    """Request model for post generation."""
    topic: Optional[str] = None
    custom_prompt: Optional[str] = None
```

This Pydantic model defines the accepted request format:
- `topic` (optional): The topic for the LinkedIn post. If not provided, the system will select one.
- `custom_prompt` (optional): A custom prompt field for future extensibility.

#### PostResponse

```python
class PostResponse(BaseModel):
    """Response model for generated post."""
    text: str
    image_url: Optional[str] = None
    status: str
```

This Pydantic model defines the response format:
- `text`: The final generated LinkedIn post text.
- `image_url` (optional): URL for any image to accompany the post.
- `status`: Status of the generation process (e.g., "success").

### Endpoints

#### POST /generate-post

```python
@app.post("/generate-post", response_model=PostResponse)
async def create_post(request: PostRequest) -> PostResponse:
    """Generate a LinkedIn post."""
    try:
        result = await generate_post(topic=request.topic)
        
        return PostResponse(
            text=result["text"],
            image_url=result.get("image_url"),
            status="success"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating post: {str(e)}"
        )
```

This endpoint:
1. Accepts a POST request with an optional topic.
2. Calls the `generate_post` function from the orchestrator.
3. Returns the generated post with a success status.
4. Handles exceptions by returning appropriate HTTP error responses.

### Application Runner

```python
if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
```

When run directly, the application starts using Uvicorn with:
- Host: 0.0.0.0 (accessible from external machines)
- Port: 8000
- Reload: Enabled for development (auto-restarts on code changes)

## Usage

### Example Request

```json
POST /generate-post
{
  "topic": "Artificial Intelligence in Healthcare"
}
```

### Example Response

```json
{
  "text": "The complete LinkedIn post content...",
  "image_url": "https://example.com/image.jpg",
  "status": "success"
}
```

### Error Response

```json
{
  "detail": "Error generating post: No topic selected for post assembly"
}
```

## Integration Points

The main.py file integrates with:
- **orchestrator.py**: Calls the `generate_post` function to run the post generation workflow.
- **Pydantic**: Uses Pydantic models for request/response validation.
- **FastAPI**: For HTTP routing and error handling.
- **Uvicorn**: As the ASGI server for running the application. 