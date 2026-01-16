import re

def normalize_arabic(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    
    # Remove Tashkeel (diacritics)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    
    # Remove Tatweel (_)
    text = re.sub(r'\u0640', '', text)
    
    # Normalize Alef
    text = re.sub(r'[أإآ]', 'ا', text)
    

    # Normalize Yeh
    text = re.sub(r'ى', 'ي', text)
    
    # Normalize Arabic Numerals
    text = text.replace('٠', '0').replace('١', '1').replace('٢', '2')\
               .replace('٣', '3').replace('٤', '4').replace('٥', '5')\
               .replace('٦', '6').replace('٧', '7').replace('٨', '8').replace('٩', '9')
               
    return text.strip()