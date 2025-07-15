from fastapi import FastAPI
import logging

PORT = 80

logger = logging.Logger("Test")
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

if __name__ == "__main__":
    import uvicorn
    import os

    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    logger.info(f"Test Server is listening to port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=is_development)