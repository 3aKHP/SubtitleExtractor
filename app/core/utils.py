import difflib

def is_text_similar(text1, text2, threshold=0.85):
    """
    判断两段文本是否高度相似 (用于过滤重复字幕)
    """
    if not text1 or not text2:
        return False
    return difflib.SequenceMatcher(None, text1, text2).ratio() > threshold

def clean_text(text):
    """简单的文本清洗"""
    return text.strip()
