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
    s = str(val)
    return re.sub(r'[^\w\s\.\-@\u0600-\u06FF]', '', s).strip()

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

def clean_dataframe(df: pd.DataFrame, config: dict, dry_run=False, exclude_cols=None):
    df = df.copy()
    report_log = []
    
    if exclude_cols is None:
        exclude_cols = []
    
    # 0. Global Sanitization
    target_cols = [c for c in df.columns if c not in exclude_cols]
    
    for col in target_cols:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()
            df[col].replace(
                to_replace=r'(?i)^\s*["\']?(nan|null|none|""|'')\s*$', 
                value=np.nan, regex=True, inplace=True
            )

    # 1. Standardize Columns
    if config.get("standardize_columns"):
        old_cols = list(df.columns)
        df.columns = [
            c.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")
            for c in df.columns
        ]
        if list(df.columns) != old_cols:
            report_log.append("✅ Standardized column names")
            exclude_cols = [c.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_") for c in exclude_cols]

    # 2. Drop Empty Rows
    if config.get("drop_empty_rows"):
        before = len(df)
        df.dropna(how='all', inplace=True)
        diff = before - len(df)
        if diff > 0:
            report_log.append(f"🗑️ Dropped {diff} empty rows")

    # 3. Fix Dates
    if config.get("fix_dates"):
        count = 0
        for col in df.columns:
            if col in exclude_cols: continue
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace('"', '').str.replace("'", "")
            
            sample = df[col].dropna().astype(str).head(15).tolist()
            if not sample: continue
            matches = sum(1 for x in sample if re.search(r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}', x))
            
            if matches >= len(sample) * 0.3:
                converted = pd.to_datetime(df[col], format='mixed', errors='coerce', dayfirst=True)
                df[col] = converted
                count += 1
        if count > 0:
            report_log.append(f"📅 Standardized dates in {count} columns")

    # 4. Money
    if config.get("clean_money"):
        count = 0
        for col in df.columns:
            if col in exclude_cols: continue
            if any(x in col.lower() for x in ['email', 'mail', 'phone', 'id', 'date', 'year', 'day']): continue
            if df[col].dtype == 'object':
                sample = "".join(df[col].dropna().astype(str).head(15).tolist()).lower()
                if re.search(r'[\$€£]|\d\s?[kmb]\b|\d,\d', sample):
                    df[col] = df[col].apply(clean_currency_value)
                    count += 1
        if count > 0:
            report_log.append(f"💰 Parsed currency/numbers in {count} columns")

    # 5. Emails
    if config.get("fix_emails"):
        report_log.append("📧 Validated emails")
        for col in df.columns:
            if col in exclude_cols: continue
            if any(k in col.lower() for k in ["email", "mail"]):
                df[col] = df[col].apply(validate_email)

    # 6. Phones
    if config.get("fix_phones"):
        report_log.append("📱 Standardized phone numbers")
        for col in df.columns:
            if col in exclude_cols: continue
            if any(k in col.lower() for k in ["phone", "mobile", "tel", "cell"]):
                df[col] = df[col].apply(clean_phone_number)

    # 7. Special Chars
    if config.get("remove_special_chars"):
        report_log.append("🧹 Removed special characters")
        for col in df.select_dtypes(include=['object']).columns:
            if col in exclude_cols: continue
            df[col] = df[col].apply(remove_special_characters)

    # 8. Arabic
    if config.get("clean_arabic"):
        report_log.append("📝 Normalized Arabic text")
        for col in df.select_dtypes(include=['object']).columns:
            if col in exclude_cols: continue
            sample = df[col].dropna().astype(str).sum()
            if re.search(r'[\u0600-\u06FF]', sample):
                df[col] = df[col].apply(normalize_arabic)

    # 9. Missing Values
    fill_rules = config.get("fill_missing", {})
    if "numeric" in fill_rules and fill_rules["numeric"]:
        report_log.append(f"🔢 Filled missing numbers with {fill_rules['numeric']}")
        for col in df.columns:
            if col in exclude_cols: continue
            if df[col].dtype.kind in 'biufc' and df[col].isnull().sum() > 0:
                method = fill_rules["numeric"]
                if method == "mean": df[col] = df[col].fillna(df[col].mean())
                elif method == "median": df[col] = df[col].fillna(df[col].median())
                elif method == "zero": df[col] = df[col].fillna(0)

    # 10. Dedupe
    if config.get("remove_duplicates"):
        dedupe_col = config.get("dedupe_column", "ALL")
        fuzzy = config.get("fuzzy_dedupe", False)
        
        if dedupe_col != "ALL" and config.get("standardize_columns"):
            dedupe_col = dedupe_col.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")

        if dedupe_col == "ALL":
            before = len(df)
            df.drop_duplicates(inplace=True)
            if len(df) < before:
                report_log.append(f"✂️ Removed {before - len(df)} exact duplicate rows")
        elif dedupe_col in df.columns:
            if not fuzzy:
                before = len(df)
                df.drop_duplicates(subset=[dedupe_col], keep='first', inplace=True)
                if len(df) < before:
                    report_log.append(f"✂️ Removed {before - len(df)} duplicates based on exact '{dedupe_col}'")
            else:
                indices_to_drop = []
                seen_texts = []
                for idx, val in df[dedupe_col].items():
                    if pd.isna(val) or val == "": continue
                    str_val = str(val)
                    if str_val in seen_texts:
                        indices_to_drop.append(idx)
                        continue
                    if seen_texts:
                        match = process.extractOne(str_val, seen_texts, scorer=fuzz.WRatio, score_cutoff=90.0)
                        if match: indices_to_drop.append(idx)
                        else: seen_texts.append(str_val)
                    else: seen_texts.append(str_val)
                if indices_to_drop:
                    df.drop(index=indices_to_drop, inplace=True)
                    report_log.append(f"🧠 Fuzzy Dedupe: Merged {len(indices_to_drop)} rows in '{dedupe_col}'")

    # 11. PRIVACY MODE
    if config.get("anonymize_pii"):
        mask_count = 0
        for col in df.columns:
            if col in exclude_cols: continue
            if any(k in col.lower() for k in ["email", "mail"]):
                df[col] = df[col].apply(mask_email)
                mask_count += 1
        for col in df.columns:
            if col in exclude_cols: continue
            if any(k in col.lower() for k in ["phone", "mobile", "tel", "cell"]):
                df[col] = df[col].apply(mask_phone)
                mask_count += 1
        for col in df.columns:
            if col in exclude_cols: continue
            if any(k in col.lower() for k in ["name", "fullname", "first_name", "last_name", "client", "customer"]):
                if "id" in col.lower(): continue 
                df[col] = df[col].apply(mask_general)
                mask_count += 1
        if mask_count > 0:
            report_log.append(f"🛡️ Privacy Mode: Anonymized PII data in {mask_count} columns.")

    return df, report_log