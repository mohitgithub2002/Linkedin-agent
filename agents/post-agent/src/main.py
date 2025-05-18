from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
from .orchestrator import generate_post
from .scraper.linkedin_post_fetcher import fetch_and_save_linkedin_data

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

class LinkedInDataRequest(BaseModel):
    """Request model for LinkedIn data fetching."""
    username: str
    page_number: Optional[int] = 1
    limit: Optional[int] = 100

class LinkedInDataResponse(BaseModel):
    """Response model for LinkedIn data."""
    data: List[Dict[str, Any]]
    file_path: str
    analysis: Optional[Dict[str, Any]] = None
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

@app.post("/fetch-linkedin-data", response_model=LinkedInDataResponse)
async def fetch_linkedin_data(request: LinkedInDataRequest) -> LinkedInDataResponse:
    """Fetch LinkedIn data using Apify and analyze it."""
    try:
        result = fetch_and_save_linkedin_data(
            username=request.username,
            page_number=request.page_number,
            limit=request.limit
        )
        
        if not result["data"]:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for user: {request.username}"
            )
        
        return LinkedInDataResponse(
            data=result["data"],
            file_path=result["file_path"],
            analysis=result["analysis"],
            status="success"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching LinkedIn data: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True) 