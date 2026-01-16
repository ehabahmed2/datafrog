import os
import tempfile

class Settings:
    APP_NAME = "DataForge Lite"
    VERSION = "1.0.0"
    # Max upload size: 100MB
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024 
    # Session timeout: 1 hour
    SESSION_TIMEOUT = 3600 
    # Temp directory for session files
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "dataforge_lite_sessions")
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

settings = Settings()

# Ensure temp dir exists
os.makedirs(settings.TEMP_DIR, exist_ok=True)