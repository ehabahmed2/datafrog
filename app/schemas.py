from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CleaningConfig(BaseModel):
    standardize_columns: bool = False
    drop_empty_rows: bool = True
    clean_arabic: bool = False
    
    remove_duplicates: bool = False
    dedupe_column: str = "ALL"
    fuzzy_dedupe: bool = False
    
    merge_active: bool = False
    merge_key_main: str = ""
    merge_key_sec: str = ""
    merge_fuzzy: bool = False
    clean_merged_columns: bool = True
    
    clean_money: bool = False
    fix_dates: bool = False
    fix_phones: bool = False
    fix_emails: bool = False
    remove_special_chars: bool = False
    
    # MUST BE HERE
    anonymize_pii: bool = False 
    
    fill_missing: Dict[str, str] = {}