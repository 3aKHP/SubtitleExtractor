import pytest
from core.alignment import AlignmentModule


@pytest.fixture
def aligner():
    return AlignmentModule()


class TestTimestamp:
    def test_format_zero(self, aligner):
        assert aligner.format_timestamp(0) == "00:00:00"

    def test_format_seconds(self, aligner):
        assert aligner.format_timestamp(65) == "00:01:05"

    def test_format_hours(self, aligner):
        assert aligner.format_timestamp(3661) == "01:01:01"

    def test_parse_valid(self, aligner):
        assert aligner.parse_timestamp("01:02:03") == 3723

    def test_parse_zero(self, aligner):
        assert aligner.parse_timestamp("00:00:00") == 0

    def test_parse_invalid_returns_zero(self, aligner):
        assert aligner.parse_timestamp("garbage") == 0

    def test_roundtrip(self, aligner):
        seconds = 7384
        assert aligner.parse_timestamp(aligner.format_timestamp(seconds)) == seconds


class TestAnalyzeNoise:
    def test_detects_watermark(self, aligner):
        # "水印" 在 OCR 里高频出现，ASR 里几乎没有
        ocr = ["水印 今天天气不错", "水印 明天有雨", "水印 后天晴"] * 5
        asr = ["今天天气不错", "明天有雨", "后天晴"]
        aligner.analyze_noise(ocr, asr)
        assert "水印" in aligner.dynamic_noise_set

    def test_no_false_positive_on_common_word(self, aligner):
        # "你好" 在 OCR 和 ASR 里都高频，不应被识别为噪音
        ocr = ["你好 世界"] * 10
        asr = ["你好 世界"] * 10
        aligner.analyze_noise(ocr, asr)
        assert "你好" not in aligner.dynamic_noise_set

    def test_empty_inputs(self, aligner):
        aligner.analyze_noise([], [])
        assert len(aligner.dynamic_noise_set) == 0


class TestAlign:
    def test_fallback_to_ocr_when_no_asr(self, aligner):
        ocr_text = "[00:00:01] 你好世界"
        result = aligner.align(ocr_text, [])
        assert result == ocr_text

    def test_align_basic(self, aligner):
        ocr_text = "[00:00:01] 你好世界\n[00:00:05] 再见"
        asr = [
            {"start": 1.0, "end": 3.0, "text": "你好世界"},
            {"start": 5.0, "end": 7.0, "text": "再见"},
        ]
        result = aligner.align(ocr_text, asr)
        assert "你好世界" in result
        assert "再见" in result

    def test_align_prefers_ocr_when_similar(self, aligner):
        # OCR 文本和 ASR 高度相似时，应采用 OCR（更准确的字形）
        ocr_text = "[00:00:01] 你好世界"
        asr = [{"start": 0.5, "end": 2.5, "text": "你好世界"}]
        result = aligner.align(ocr_text, asr)
        assert "你好世界" in result

    def test_align_falls_back_to_asr_when_no_ocr_match(self, aligner):
        # OCR 时间窗口内没有匹配，应保留 ASR 原文
        ocr_text = "[00:10:00] 完全不相关的内容"
        asr = [{"start": 1.0, "end": 3.0, "text": "独立的ASR内容"}]
        result = aligner.align(ocr_text, asr)
        assert "独立的ASR内容" in result
