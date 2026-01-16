import pandas as pd
import numpy as np
from datetime import datetime, date

def make_json_safe(obj):
    """Recursively convert numpy/pandas types to Python native types."""
    # 1. Handle None explicitly first
    if obj is None:
        return None
        
    # 2. Handle Collection Types (Lists, Dicts, DataFrames) BEFORE scalar checks
    # This prevents pd.isna() from being called on a list/array and raising ValueError
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return [make_json_safe(x) for x in obj.tolist()]
    if isinstance(obj, np.ndarray):
        return [make_json_safe(x) for x in obj.tolist()]
    if isinstance(obj, list):
        return [make_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    # 3. Handle Scalar Types
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    
    # 4. Handle Numbers and NaN
    # Now it is safe to check pd.isna because lists/arrays are handled above
    try:
        if pd.isna(obj): 
            return None
    except:
        pass # Fallback if pd.isna fails on weird types
        
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
        
    return obj