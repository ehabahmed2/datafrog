# ⚒️ DataForge Lite
**Secure. Offline. Intelligent Data Cleaning.**

DataForge Lite is a production-grade, local-only tool designed to clean messy Excel and CSV datasets instantly. It combines robust rule-based cleaning with **AI-powered Fuzzy Logic**, all without your data ever leaving your computer.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-yellow) ![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-green)

---

## 🚀 Why DataForge Lite?

*   **100% Privacy:** No cloud APIs. No databases. Your files never leave your machine. Perfect for GDPR/HIPAA sensitive data.
*   **The "Killer" Features:** 
    *   **Fuzzy Dedupe:** Finds duplicates that look similar but aren't identical (e.g., "Ahmed" vs "Ahmad").
    *   **Smart VLOOKUP:** Merges two messy files using AI matching.
    *   **Privacy Mode:** Masks sensitive data instantly for safe sharing.
*   **Arabic-First Support:** Specialized logic to normalize Arabic text, remove Tashkeel, and unify Alef/Yeh forms.


---

## ✨ Features Breakdown

### 🔧 Basic Cleaning
*   **Standardize Headers:** Converts messy headers to clean `snake_case` (e.g., "Phone Number" → `phone_number`).
*   **Smart Empty Removal:** Detects and removes rows that are empty or contain "nan", "null", "NULL", or invisible whitespace.
*   **Numeric Fill:** Automatically fill missing numbers with **Zero**, **Mean**, or **Median**.

### 🛠️ Advanced Toolkit (Edge Cases)
*   **💰 Money Parser:** Fixes messy currencies like `$3,500`, `4.2k`, `1.5M`, `€ 50` → converts to pure numbers (`3500.0`, `4200.0`).
*   **📅 Smart Dates:** Auto-detects mixed formats (US vs EU) and converts to ISO standard (`YYYY-MM-DD`). Handles quotes (`"01-15-2023"`) and slashes.
*   **📧 Email Repair:** Validates formats and auto-fixes typos like `name@@gmail.com` → `name@gmail.com`.
*   **📱 Phone Standardizer:** Strips formatting, keeps leading zeros/plus signs (e.g., `(202) 555-0100` → `2025550100`).
*   **🗑️ Noise Removal:** Strips special characters like `*`, `?`, `^`, `#` from text fields.

### 👑 The Killer Features (AI & Security)

#### 1. 🧠 Smart Deduplication (Fuzzy AI)
*   **Exact Dedupe:** Remove 100% identical rows.
*   **Column Dedupe:** Target specific columns (e.g., "Only remove if Email is duplicated").
*   **Fuzzy Matching:** Uses Levenshtein distance to find typos.
    *   *Example:* Merges "Coca-Cola" and "Coca Cola Inc" automatically.

#### 2. 📂 Smart VLOOKUP (Data Enrichment)
*   Upload a **Main File** (e.g., Leads) and a **Lookup File** (e.g., Region Data).
*   Merge them instantly based on a key column.
*   **Fuzzy Join:** Matches data even if the spelling differs slightly between files.

#### 3. 🛡️ Privacy Mode (GDPR Compliance)
*   Instantly masks PII (Personally Identifiable Information) before sharing files.
*   **Emails:** `ahmed@example.com` → `a****@example.com`
*   **Phones:** `202-555-0100` → `***-***-0100`
*   **Names:** `Ahmed Ali` → `A**** A**`

---

## 📦 Installation & Usage

### Option A: For Developers (Running from Source)

1.  **Clone the Repo**
    ```bash
    git clone https://github.com/your-repo/dataforge-lite.git
    cd dataforge-lite
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Install Requirements**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the App**
    ```bash
    python run.py
    ```
    The app will auto-launch in your browser at `http://127.0.0.1:8000`.

### Option B: Build Portable Executable (.exe)
Want to send this tool to a client who doesn't have Python? Build a standalone executable.

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Run the build command (Windows):
    ```bash
    pyinstaller --noconfirm --onefile --windowed --name "DataForgeLite" --add-data "app/static;app/static" run.py
    ```
    *(Note: On Mac/Linux, replace `;` with `:` in the add-data flag)*.

3.  Your app is ready in the `dist/` folder!

---

## 🧪 Testing
Run the automated test suite to ensure all logic is working correctly:
```bash
python -m pytest
```
### 📜 License

MIT License
You are free to use, modify, and distribute this software.

--- 
### ⭐ Final Note

DataForge Lite is not a toy script.
It’s a real-world, sellable, production-grade tool built for people who care about:

Data privacy
Accuracy
Speed
Simplicity

If Excel failed you... this won’t.


need help? 
email: ihapbpc@gmail.com

Built with ❤️ using Python, FastAPI & RapidFuzz.
