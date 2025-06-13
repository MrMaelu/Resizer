import re

def clean_window_title(title, sanitize=False):
    if not title:
        return ""
    
    # Basic cleaning
    title = re.sub(r'[^\x20-\x7E]', '', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.strip().lower()
    
    if sanitize:
        # Additional cleaning for config files
        parts = re.split(r' [-—–] ', title)
        title = parts[-1].strip()
        title = re.sub(r'\s*\(.*\)$', '', title)
        title = re.sub(r'\s+\d+%$', '', title)
    
    return title

