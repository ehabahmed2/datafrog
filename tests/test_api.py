import sys
import os
import pytest
from fastapi.testclient import TestClient

# Path fix
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.main import app

client = TestClient(app)

DATA_DIR = os.path.join(current_dir, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "test.csv")

def create_test_csv():
    """Helper to create a fresh CSV with EXACT duplicates"""
    with open(CSV_PATH, "w", encoding="utf-8") as f:
        # Note: Row 3 is now identical to Row 1 (id=1)
        f.write("id,name,value\n1,Ahmed,10\n2,Mohamed, \n1,Ahmed,10\n")

def test_upload():
    create_test_csv() # Create file before upload
    
    with open(CSV_PATH, "rb") as f:
        response = client.post("/api/upload", files={"file": ("test.csv", f, "text/csv")})
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    return data["session_id"]

def test_preview():
    sid = test_upload()
    config = {"remove_duplicates": True, "fill_missing": {"numeric": "zero"}}
    response = client.post(f"/api/preview/{sid}", json=config)
    assert response.status_code == 200
    data = response.json()
    assert "diff_summary" in data

def test_clean():
    sid = test_upload()
    config = {"remove_duplicates": True}
    response = client.post(f"/api/clean/{sid}", json=config)
    assert response.status_code == 200
    data = response.json()
    # Now this should pass: 3 original rows -> 2 unique rows
    assert data["cleaned_rows"] == 2
    assert "download_url" in data