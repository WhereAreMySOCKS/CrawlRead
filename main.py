from fastapi import FastAPI
import uvicorn
from app.api.endpoints import router as api_router

app = FastAPI(
    title="CrawlRead API",
    description="API for CrawlRead application",
    version="0.1.0"
)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


# Include API routes
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)