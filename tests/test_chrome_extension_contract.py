from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_popup_posts_current_extract_request_fields():
    popup_js = read("chrome_extension/popup.js")

    assert "roi_bottom" in popup_js
    assert "roi_top" in popup_js
    assert "enable_asr" in popup_js
    assert "model_size" in popup_js
    assert "roi:" not in popup_js


def test_popup_keeps_asr_opt_in_by_default():
    popup_html = read("chrome_extension/popup.html")

    assert 'id="asr-check"' in popup_html
    assert 'id="asr-check" checked' not in popup_html
