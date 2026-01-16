import os
import threading
import time
import shutil
import traceback
import uuid
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import signal
# App specific imports
from app.config import settings
from app.utils.file_handler import read_file_as_df
from app.core.cleaner import clean_dataframe
from app.core.reporter import compute_diff
from app.schemas import CleaningConfig
from app.utils.json_utils import make_json_safe
from app.core.merger import fuzzy_merge_datasets

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS (Localhost access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Session Store (In-Memory)
SESSIONS = {}

def cleanup_sessions():
    """Background task to remove expired sessions and files."""
    while True:
        try:
            now = time.time()
            expired_ids = []
            for sid, data in SESSIONS.items():
                if now - data['created_at'] > settings.SESSION_TIMEOUT:
                    expired_ids.append(sid)
            
            for sid in expired_ids:
                session_dir = os.path.join(settings.TEMP_DIR, sid)
                if os.path.exists(session_dir):
                    shutil.rmtree(session_dir, ignore_errors=True)
                del SESSIONS[sid]
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(60)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
cleanup_thread.start()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(400, "File too large")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type")

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(settings.TEMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    file_path = os.path.join(session_dir, f"original{ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Initial Analysis
    try:
        df = read_file_as_df(file_path)
    except Exception as e:
        shutil.rmtree(session_dir)
        raise HTTPException(400, f"Failed to read file: {str(e)}")

    # Store in session
    SESSIONS[session_id] = {
        "created_at": time.time(),
        "files": {"original": file_path},
        "original_filename": file.filename
    }
    
    analysis = {
        "rows": len(df),
        "columns": list(df.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.apply(lambda x: str(x)).to_dict(),
        "preview": df.head(5).to_dict(orient="records")
    }
    
    return make_json_safe({
        "session_id": session_id, 
        "analysis": analysis
    })


@app.post("/api/upload-secondary/{session_id}")
async def upload_secondary(session_id: str, file: UploadFile = File(...)):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
        
    session_dir = os.path.join(settings.TEMP_DIR, session_id)
    ext = os.path.splitext(file.filename)[1].lower()
    file_path = os.path.join(session_dir, f"secondary{ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Analyze quickly
    try:
        df = read_file_as_df(file_path)
    except Exception as e:
        raise HTTPException(400, "Invalid Secondary File")
        
    SESSIONS[session_id]["files"]["secondary"] = file_path
    
    return make_json_safe({
        "columns": list(df.columns),
        "rows": len(df)
    })


@app.post("/api/preview/{session_id}")
async def preview_cleaning(session_id: str, config: CleaningConfig):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    session_data = SESSIONS[session_id]
    original_path = session_data["files"]["original"]
    
    try:
        df_orig = read_file_as_df(original_path)
        report_log = [] # Collects actions for the UI
        
        # 1. APPLY MERGE IF ACTIVE
        added_cols = []
        if config.merge_active and "secondary" in session_data["files"]:
            sec_path = session_data["files"]["secondary"]
            df_sec = read_file_as_df(sec_path)
            
            # Unpack 3 values (df, count, columns_added)
            df_orig, merged_count, added_cols = fuzzy_merge_datasets(
                df_orig, df_sec, 
                config.merge_key_main, config.merge_key_sec, config.merge_fuzzy
            )
            if merged_count > 0:
                report_log.append(f"🔗 Merged/Enriched {merged_count} rows from Lookup File")
            else:
                report_log.append("⚠️ Merge active but 0 rows matched (check your keys?)")

        # 2. DETERMINE EXCLUSIONS
        # If user does NOT want to clean merged columns, we add them to exclusion list
        exclude_list = []
        if not config.clean_merged_columns:
            exclude_list = added_cols

        # 3. RUN CLEANER
        df_clean, clean_log = clean_dataframe(df_orig, config.model_dump(), dry_run=True, exclude_cols=exclude_list)
        
        # Combine logs
        full_log = report_log + clean_log

        # 4. COMPUTE DIFF
        # Reload raw for accurate Diff (Raw vs Cleaned)
        raw_df = read_file_as_df(original_path) 
        diff = compute_diff(raw_df, df_clean, max_items=20)
        
        return {
            "diff_summary": diff,
            "report_log": full_log, # Send log to frontend
            "preview_clean": make_json_safe(df_clean.head(5).to_dict(orient="records"))
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.post("/api/clean/{session_id}")
async def apply_cleaning(session_id: str, config: CleaningConfig):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
        
    session_data = SESSIONS[session_id]
    original_path = session_data["files"]["original"]
    
    try:
        df_orig = read_file_as_df(original_path)
        report_log = []
        
        # 1. APPLY MERGE
        added_cols = []
        if config.merge_active and "secondary" in session_data["files"]:
            sec_path = session_data["files"]["secondary"]
            df_sec = read_file_as_df(sec_path)
            
            df_orig, merged_count, added_cols = fuzzy_merge_datasets(
                df_orig, df_sec, 
                config.merge_key_main, config.merge_key_sec, config.merge_fuzzy
            )
            report_log.append(f"🔗 Merged/Enriched {merged_count} rows from Lookup File")

        # 2. DETERMINE EXCLUSIONS
        exclude_list = []
        if not config.clean_merged_columns:
            exclude_list = added_cols
            
        # 3. RUN CLEANER
        df_clean, clean_log = clean_dataframe(df_orig, config.model_dump(), exclude_cols=exclude_list)
        
        report_log.extend(clean_log)
        
        # 4. SAVE RESULT
        orig_filename = session_data["original_filename"]
        base, ext = os.path.splitext(orig_filename)
        cleaned_filename = f"{base}_cleaned{ext}"
        cleaned_path = os.path.join(settings.TEMP_DIR, session_id, cleaned_filename)
        
        if ext == ".csv":
            df_clean.to_csv(cleaned_path, index=False, encoding='utf-8-sig', na_rep='')
        else:
            df_clean.to_excel(cleaned_path, index=False)
            
        session_data["files"]["cleaned"] = cleaned_path
        
        # 5. GENERATE DIFF
        raw_df = read_file_as_df(original_path)
        diff = compute_diff(raw_df, df_clean, max_items=100)
        
        return {
            "status": "success",
            "cleaned_rows": len(df_clean),
            "report_log": report_log,
            "diff_summary": diff,
            "download_url": f"/api/download/{session_id}/cleaned"
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Cleaning failed: {str(e)}")


@app.get("/api/download/{session_id}/{file_type}")
async def download_file(session_id: str, file_type: str):
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
        
    files = SESSIONS[session_id]["files"]
    
    if file_type == "cleaned":
        if "cleaned" not in files:
            raise HTTPException(404, "Cleaned file not generated yet")
        return FileResponse(files["cleaned"], filename=os.path.basename(files["cleaned"]))
        
    raise HTTPException(400, "Invalid file type")


# ... (existing code) ...

@app.get("/api/health")
async def health_check():
    """Used by the launcher to see if the app is already running."""
    return {"status": "ok", "app": "DataForg"}

@app.post("/api/shutdown")
async def shutdown():
    """Kills the server process."""
    # Run in a thread to allow the response to return first
    def kill():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Thread(target=kill).start()
    return {"message": "Shutting down..."}


# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")