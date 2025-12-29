from pydantic import BaseModel, HttpUrl

class PostCreate(BaseModel):
    title: str
    content: str
    
class PostResponse(BaseModel):
    title: str
    content: str