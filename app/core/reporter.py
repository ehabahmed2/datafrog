import pandas as pd
import numpy as np
import math
from app.utils.json_utils import make_json_safe

def compute_diff(original_df, cleaned_df, max_items=50):
    """
    Compares two dataframes.
    Counts ALL differences, but only returns previews for the first 'max_items'.
    """
    orig_idx = set(original_df.index)
    clean_idx = set(cleaned_df.index)
    
    removed_ids = list(orig_idx - clean_idx)
    common_idx = list(orig_idx.intersection(clean_idx))
    common_idx.sort()
    
    # Capture Removed Rows Data (Preview Limit 20)
    removed_preview = []
    for rid in removed_ids[:20]:
        try:
            row_data = original_df.loc[rid].to_dict()
            removed_preview.append({
                "row_index": int(rid) + 1,
                "data": row_data
            })
        except:
            pass

    # Optimization
    df_orig_common = original_df.loc[common_idx]
    df_clean_common = cleaned_df.loc[common_idx]
    
    cols_orig = list(original_df.columns)
    cols_clean = list(cleaned_df.columns)
    
    num_cols_to_compare = min(len(cols_orig), len(cols_clean))
    
    changed_rows = []
    count_diffs = 0
    truncated = False
    
    # Iterate through ALL common rows to get accurate stats
    for idx in common_idx:
        row_orig = df_orig_common.loc[idx]
        row_clean = df_clean_common.loc[idx]
        
        row_changes = {}
        has_change = False
        
        # Compare columns by position
        for i in range(num_cols_to_compare):
            col_name = cols_clean[i] 
            val_a = row_orig.iloc[i]
            val_b = row_clean.iloc[i]
            
            try:
                is_diff = False
                a_is_nan = pd.isna(val_a) or val_a is None or val_a == ""
                b_is_nan = pd.isna(val_b) or val_b is None or val_b == ""
                
                # Compare Logic
                if a_is_nan and b_is_nan: continue
                if a_is_nan != b_is_nan: is_diff = True
                elif str(val_a).strip() != str(val_b).strip(): is_diff = True
                        
                if is_diff:
                    row_changes[col_name] = {"before": val_a, "after": val_b}
                    has_change = True
            except: pass
        
        if has_change:
            count_diffs += 1
            # Only add to preview if under limit
            if len(changed_rows) < max_items:
                changed_rows.append({
                    "row_index": int(idx) + 1,
                    "changes": row_changes
                })
            else:
                truncated = True

    return make_json_safe({
        "stats": {
            "total_original": len(original_df),
            "total_cleaned": len(cleaned_df),
            "removed_count": len(removed_ids),
            "changed_count": count_diffs # This is now the TRUE count
        },
        "changed_rows": changed_rows,
        "removed_preview": removed_preview,
        "truncated": truncated
    })