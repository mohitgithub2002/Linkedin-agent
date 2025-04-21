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