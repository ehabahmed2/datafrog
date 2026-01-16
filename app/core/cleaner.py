import pandas as pd
import numpy as np
import re
from rapidfuzz import process, fuzz
from app.core.arabic import normalize_arabic

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def clean_currency_value(val):
    s = str(val).lower().strip()
    if s == 'nan' or s == '': return np.nan
    
    multiplier = 1
    if s.endswith('k'):
        multiplier = 1000
        s = s[:-1]
    elif s.endswith('m'):
        multiplier = 1000000
        s = s[:-1]
    elif s.endswith('b'):
        multiplier = 1000000000
        s = s[:-1]
    
    s = re.sub(r'[^\d\.\-]', '', s)
    try:
        if not s or s == '.' or s == '-': return np.nan
        return float(s) * multiplier
    except:
        return np.nan

def clean_phone_number(val):
    s = str(val).strip()
    if not s or s.lower() == 'nan': return np.nan
    has_plus = s.startswith('+') or s.startswith('(+')
    clean = re.sub(r'[^\d]', '', s)
    if len(clean) < 3: return np.nan
    return f"+{clean}" if has_plus else clean

def validate_email(val):
    s = str(val).strip().lower()
    s = s.replace('@@', '@')
    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$', s):
        return s
    return np.nan

def remove_special_characters(val):
    if pd.isna(val): return val
    s = str(val).strip()
    # Skip JSON/List objects
    if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
        return val
    # Allow URL chars and basic punctuation
    return re.sub(r'[^\w\s\.\-@:/\(\)\&]', '', s).strip()

def mask_email(val):
    s = str(val).strip()
    if not s or s.lower() == 'nan': return val
    if '@' in s:
        user, domain = s.split('@', 1)
        if len(user) > 1:
            return f"{user[0]}****@{domain}"
        return f"*@{domain}"
    return s

def mask_phone(val):
    s = str(val).strip()
    if not s or s.lower() == 'nan': return val
    if len(s) > 4:
        return "*" * (len(s) - 4) + s[-4:]
    return "*" * len(s)

def mask_general(val):
    s = str(val).strip()
    if not s or s.lower() == 'nan': return val
    if len(s) > 1:
        return s[0] + "*" * 4
    return "*"

# ==========================================
# MAIN CLEANING ENGINE
# ==========================================
# --- MAIN ENGINE ---
def clean_dataframe(df: pd.DataFrame, config: dict, dry_run=False, exclude_cols=None):
    df = df.copy()
    report_log = []
    
    # 1. Build Exclusion List
    # Combines system exclusions (from merge) + User selected exclusions
    if exclude_cols is None: exclude_cols = []
    
    user_ignores = config.get("ignore_columns", [])
    
    # Normalize user ignores to match dataframe columns
    if config.get("standardize_columns"):
        user_ignores = [c.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_") for c in user_ignores]
    
    # Combine lists
    final_exclusions = list(set(exclude_cols + user_ignores))

    # ---------------------------------------------------------
    # STEP 0: GLOBAL SANITIZATION 
    # ---------------------------------------------------------
    target_cols = [c for c in df.columns if c not in final_exclusions]
    
    for col in target_cols:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
            df[col].replace(r'(?i)^\s*["\']?(nan|null|none|""|'')\s*$', np.nan, regex=True, inplace=True)

    # 1. Standardize Columns
    if config.get("standardize_columns"):
        old_cols = list(df.columns)
        df.columns = [c.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_") for c in df.columns]
        if list(df.columns) != old_cols:
            report_log.append("✅ Standardized column names")
            # Re-normalize exclusions to match new names
            final_exclusions = [c.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_") for c in final_exclusions]

    # 2. Drop Empty Rows
    if config.get("drop_empty_rows"):
        before = len(df)
        df.dropna(how='all', inplace=True)
        if len(df) < before: report_log.append(f"🗑️ Dropped {before - len(df)} empty rows")

    # 3. Fix Dates
    if config.get("fix_dates"):
        count = 0
        for col in df.columns:
            if col in final_exclusions: continue
            sample = df[col].dropna().astype(str).head(15).tolist()
            if not sample: continue
            matches = sum(1 for x in sample if re.search(r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}', x))
            if matches >= len(sample) * 0.3:
                converted = pd.to_datetime(df[col], format='mixed', errors='coerce', dayfirst=True)
                if converted.notna().sum() > 0:
                    df[col] = converted
                    count += 1
        if count > 0: report_log.append(f"📅 Standardized dates in {count} columns")

    # 4. Money
    if config.get("clean_money"):
        count = 0
        for col in df.columns:
            if col in final_exclusions: continue
            # HARDCODED SAFETY: Never touch these columns for money
            if any(x in col.lower() for x in ['email', 'phone', 'id', 'date', 'year', 'day', 'zip', 'address', 'street', 'location']): continue
            
            if df[col].dtype == 'object':
                sample = df[col].dropna().astype(str).head(15).tolist()
                if not sample: continue
                # Strict check: Must have digit AND currency symbol OR 'k/m/b' suffix
                money_matches = sum(1 for x in sample if re.search(r'[\$€£]|\d', x) and re.search(r'[\d\$€£][\d,\.kmb]+', x.lower()))
                
                if money_matches >= len(sample) * 0.3:
                    df[col] = df[col].apply(clean_currency_value)
                    count += 1
        if count > 0: report_log.append(f"💰 Parsed currency in {count} columns")

    # 5. Emails
    if config.get("fix_emails"):
        for col in df.columns:
            if col in final_exclusions: continue
            if any(k in col.lower() for k in ["email", "mail"]):
                df[col] = df[col].apply(validate_email)

    # 6. Phones
    if config.get("fix_phones"):
        for col in df.columns:
            if col in final_exclusions: continue
            if any(k in col.lower() for k in ["phone", "mobile", "tel", "cell"]):
                df[col] = df[col].apply(clean_phone_number)

    # 7. Special Chars
    if config.get("remove_special_chars"):
        for col in df.select_dtypes(include=['object']).columns:
            if col in final_exclusions: continue
            df[col] = df[col].apply(remove_special_characters)

    # 8. Arabic
    if config.get("clean_arabic"):
        for col in df.select_dtypes(include=['object']).columns:
            if col in final_exclusions: continue
            if re.search(r'[\u0600-\u06FF]', df[col].dropna().astype(str).sum()):
                df[col] = df[col].apply(normalize_arabic)

    # 9. Missing
    fill_rules = config.get("fill_missing", {})
    if "numeric" in fill_rules and fill_rules["numeric"]:
        for col in df.columns:
            if col in final_exclusions: continue
            if df[col].dtype.kind in 'biufc' and df[col].isnull().sum() > 0:
                m = fill_rules["numeric"]
                if m == "mean": df[col] = df[col].fillna(df[col].mean())
                elif m == "median": df[col] = df[col].fillna(df[col].median())
                elif m == "zero": df[col] = df[col].fillna(0)

    # 10. Dedupe
    if config.get("remove_duplicates"):
        d_col = config.get("dedupe_column", "ALL")
        if d_col != "ALL" and config.get("standardize_columns"):
            d_col = d_col.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")

        if d_col == "ALL":
            orig_len = len(df)
            df.drop_duplicates(inplace=True)
            if len(df) < orig_len: report_log.append(f"✂️ Removed {orig_len - len(df)} duplicates")
        elif d_col in df.columns:
            if not config.get("fuzzy_dedupe"):
                orig_len = len(df)
                df.drop_duplicates(subset=[d_col], inplace=True)
                if len(df) < orig_len: report_log.append(f"✂️ Removed {orig_len - len(df)} duplicates")
            else:
                # Fuzzy
                to_drop = []
                seen = []
                for idx, val in df[d_col].items():
                    s = str(val)
                    if not s: continue
                    if seen and process.extractOne(s, seen, scorer=fuzz.WRatio, score_cutoff=90):
                        to_drop.append(idx)
                    else:
                        seen.append(s)
                if to_drop:
                    df.drop(index=to_drop, inplace=True)
                    report_log.append(f"🧠 Fuzzy: Merged {len(to_drop)} rows")

    # 11. Privacy
    if config.get("anonymize_pii"):
        mask_c = 0
        for col in df.columns:
            if col in final_exclusions: continue
            cl = col.lower()
            if "mail" in cl: df[col] = df[col].apply(mask_email); mask_c+=1
            elif "phone" in cl: df[col] = df[col].apply(mask_phone); mask_c+=1
            elif any(x in cl for x in ['name', 'client']) and 'id' not in cl: df[col] = df[col].apply(mask_general); mask_c+=1
        if mask_c: report_log.append(f"🛡️ Privacy: Masked PII in {mask_c} cols")

    return df, report_log