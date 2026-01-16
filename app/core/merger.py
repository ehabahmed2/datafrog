import pandas as pd
from rapidfuzz import process, fuzz
import numpy as np
import re

def normalize_key_for_merge(text):
    """
    Aggressive normalization: removes non-alphanumeric chars.
    'Coca-Cola Co.' -> 'cocacolaco'
    """
    if pd.isna(text) or text == "":
        return ""
    s = str(text).lower()
    return re.sub(r'[^\w]', '', s)

def fuzzy_merge_datasets(df_main, df_sec, key_main, key_sec, fuzzy=True, threshold=75.0):
    """
    Performs a Left Join (VLOOKUP) from df_sec into df_main.
    """
    try:
        df_main = df_main.copy()
        df_sec = df_sec.copy()
        
        # 1. Handle Column Name Collisions
        # If File 2 has "Email" and File 1 has "Email", rename File 2's to "Email_lookup"
        rename_map = {}
        for col in df_sec.columns:
            if col == key_sec: continue 
            
            if col in df_main.columns:
                new_name = f"{col}_lookup"
                counter = 1
                while new_name in df_main.columns:
                    new_name = f"{col}_lookup_{counter}"
                    counter += 1
                rename_map[col] = new_name
        
        if rename_map:
            df_sec.rename(columns=rename_map, inplace=True)

        # 2. Identify Columns to Add
        cols_to_add = [c for c in df_sec.columns if c != key_sec]
        
        # Initialize them in Main DF
        for col in cols_to_add:
            df_main[col] = None

        if key_main not in df_main.columns or key_sec not in df_sec.columns:
            return df_main, 0, []

        # 3. Build Lookup Map
        sec_map = {}
        sec_keys_clean = []
        
        for idx, val in df_sec[key_sec].items():
            if pd.isna(val): continue
            clean_k = normalize_key_for_merge(val)
            if not clean_k: continue
            
            if clean_k not in sec_map:
                sec_map[clean_k] = idx
                sec_keys_clean.append(clean_k)

        # 4. Perform Match
        merged_count = 0
        
        for idx, row in df_main.iterrows():
            val = row[key_main]
            val_clean = normalize_key_for_merge(val)
            
            if not val_clean:
                continue
                
            match_idx = None
            
            # A) Exact Match
            if val_clean in sec_map:
                match_idx = sec_map[val_clean]
            
            # B) Fuzzy Match
            elif fuzzy:
                res = process.extractOne(
                    val_clean, 
                    sec_keys_clean, 
                    scorer=fuzz.WRatio, 
                    score_cutoff=threshold
                )
                if res:
                    match_clean_key = res[0]
                    match_idx = sec_map[match_clean_key]
            
            # C) Copy Data
            if match_idx is not None:
                for col in cols_to_add:
                    try:
                        source_val = df_sec.at[match_idx, col]
                        df_main.at[idx, col] = source_val
                    except: pass
                merged_count += 1

        return df_main, merged_count, cols_to_add

    except Exception as e:
        import traceback
        traceback.print_exc()
        return df_main, 0, []