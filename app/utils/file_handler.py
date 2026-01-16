import pandas as pd
import csv
import io
import os

def read_file_as_df(file_path):
    """
    Reads CSV or Excel.
    Includes SMART REPAIR for bad CSV lines (e.g. "$3,500" unquoted).
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.xlsx', '.xls']:
        try:
            return pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Excel read error: {e}")
    
    if ext == '.csv':
        try:
            # 1. Try standard fast read
            return pd.read_csv(file_path, on_bad_lines='error')
        except:
            # 2. Fallback: Robust Line-by-Line Parsing
            return _read_csv_robust(file_path)
            
    raise ValueError("Unsupported file format")

def _read_csv_robust(file_path):
    """
    Manually parses CSV to recover rows with extra commas (common in money fields).
    """
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"File open error: {e}")
        
    if not lines:
        return pd.DataFrame()
        
    # Parse Header
    try:
        reader = csv.reader([lines[0]])
        header = next(reader)
        expected_cols = len(header)
    except:
        return pd.DataFrame() # Empty or invalid
    
    good_rows = []
    
    for line in lines[1:]:
        if not line.strip(): continue
        # Parse row using CSV standard (handles quotes correctly)
        try:
            row = next(csv.reader([line]))
        except:
            continue
        
        # Exact match? Good.
        if len(row) == expected_cols:
            good_rows.append(row)
            
        # Too many columns? (e.g. 7 instead of 6) -> Try to Repair
        elif len(row) == expected_cols + 1:
            repaired = False
            # Iterate and try to merge two adjacent fields if they look like a split number
            # e.g. ["$3", "500"] -> "$3,500"
            for i in range(len(row) - 1):
                part_a = row[i].strip()
                part_b = row[i+1].strip()
                
                # Heuristic: part_a ends with digit or symbol, part_b starts with digit
                # OR part_a starts with money symbol
                if (part_a and (part_a[-1].isdigit() or part_a.startswith('$') or part_a.startswith('€') or part_a.startswith('£'))) and \
                   (part_b and part_b[0].isdigit()):
                    
                    # Merge them
                    new_val = f"{part_a},{part_b}"
                    new_row = row[:i] + [new_val] + row[i+2:]
                    
                    if len(new_row) == expected_cols:
                        good_rows.append(new_row)
                        repaired = True
                        break
    
    return pd.DataFrame(good_rows, columns=header)