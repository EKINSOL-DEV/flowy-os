import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PORT = 8080

# Create logs directory if it doesn't exist
log_dir = '/flowy/logs/wifi-web'
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, 'wifi_web.log')
handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)  # 10MB per log file
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger("wifi_web")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Initialize FastAPI app
app = FastAPI(
    title="WiFi Web Interface",
    description="Web interface for WiFi management",
    version="1.0.0"
)

# Get the directory where this script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
site_dir = os.path.join(current_dir, "site")

# Mount static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory=site_dir), name="static")

@app.get("/")
async def read_root():
    """Serve the main index.html file"""
    response = FileResponse(os.path.join(site_dir, "index.html"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/style.css")
async def get_css():
    """Serve the CSS file"""
    response = FileResponse(os.path.join(site_dir, "style.css"))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/script.js")
async def get_js():
    """Serve the JavaScript file"""
    response = FileResponse(os.path.join(site_dir, "script.js"), media_type="application/javascript")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/lucide.js")
async def get_lucide():
    """Serve the Lucide JavaScript file"""
    response = FileResponse(os.path.join(site_dir, "lucide.js"), media_type="application/javascript")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import os

    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    logger.info(f"WiFi Web Server is listening on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=is_development)