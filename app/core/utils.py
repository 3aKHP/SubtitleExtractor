import difflib

def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def is_duplicate(text: str, history: list, threshold: float) -> bool:
    """判断 text 是否与 history 中某条高度相似或被包含。"""
    for old in history:
        if text == old:
            return True
        if text_similarity(text, old) > threshold:
            return True
        if text in old and len(old) - len(text) < 5:
            return True
    return False

def clean_text(text: str) -> str:
    return text.strip()
