from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit

import shutil
import tempfile
import os
import uuid

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

text_posts = {
    1:{
    "title": "First Post",
    "content": "This is the content of the first post"
},
    2:{
    "title": "First Post",
    "content": "This is the content of the first post"
}, 
    3:{
    "title": "First Post",
    "content": "This is the content of the first post"
}
}

@app.get("/posts")
def get_all_posts(limit:int = None):
    if limit:
        return list(text_posts.values())[:limit]
    return text_posts

@app.get("/posts/{id}")    
def get_post_by_id(id: int) -> PostResponse: 
    if id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    return text_posts.get(id)

@app.post("/posts")
def create_post(post: PostCreate) -> PostResponse: 
    new_post = {
        "title": post.title,
        "content": post.content,
    }
    text_posts[len(text_posts)+1] = new_post
    return new_post

@app.delete("/posts/{id}")
def delete_post(id: int):
    if id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    deleted_post = text_posts.pop(id)
    return {"detail": "Post deleted successfully", "post": deleted_post}     


@app.post('/upload')
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(...),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False ,suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path, 'rb'),
            file_name=file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_names=True,
                tags=['backend-upload']

            )
        ) 

        if upload_result.response_metadata.status == 200:
             post = Post(caption=caption, url=upload_result.url, file_type='video' if file.content_type.startswith('video') else 'image', file_name=upload_result.name)
             session.add(post)
             await session.commit()
             await session.refresh(post)
             return post

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()    

   

@app.get('/feed')    
async def get_feed(session: AsyncSession = Depends(get_async_session)):
    posts = await session.execute(select(Post).order_by(Post.created_at.desc()))
    return [row[0] for row in posts.all()]

    posts_data = []
    for post in posts:
        posts_data.append({
            "id":str(post.id),
            "caption":post.caption,
            "url":post.url,
            "file_type":post.file_type,
            "filename":post.filename,
            "created_at":post.created_at.isoformat()
        })
    return {"posts": posts_data}    