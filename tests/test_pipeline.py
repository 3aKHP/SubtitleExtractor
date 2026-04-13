import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch


def make_mock_ocr(texts):
    """返回一个 OCREngine mock，依次返回 texts 列表里的文本。"""
    engine = MagicMock()
    engine.recognize.side_effect = texts
    return engine


def make_mock_processor(frames):
    """
    返回一个 VideoProcessor mock。
    frames: list of (roi_image, timestamp, frame_id)
    """
    proc = MagicMock()
    proc.total_frames = max((f[2] for f in frames), default=1)
    proc.extract_subtitle_frames.return_value = iter(frames)
    return proc


class TestRunOcr:
    def test_writes_output_file(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frames = [(dummy_frame, "00:00:01", 10)]
        ocr = make_mock_ocr(["你好世界"])

        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            result = run_ocr(
                video_path="fake.mp4",
                output_dir=str(tmp_path),
                ocr_engine=ocr,
            )

        out_file = tmp_path / "subtitle_fake.txt"
        assert out_file.exists()
        assert "你好世界" in out_file.read_text(encoding="utf-8")
        assert "你好世界" in result

    def test_deduplication(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        # 同一句话出现三次，应只保留一条
        frames = [
            (dummy_frame, "00:00:01", 10),
            (dummy_frame, "00:00:02", 20),
            (dummy_frame, "00:00:03", 30),
        ]
        ocr = make_mock_ocr(["你好世界", "你好世界", "你好世界"])

        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            result = run_ocr("fake.mp4", str(tmp_path), ocr)

        assert result.count("你好世界") == 1

    def test_empty_ocr_skipped(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frames = [(dummy_frame, "00:00:01", 10)]
        ocr = make_mock_ocr([""])  # OCR 返回空

        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            result = run_ocr("fake.mp4", str(tmp_path), ocr)

        assert result == ""

    def test_progress_callback_called(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frames = [(dummy_frame, "00:00:01", 10)]
        ocr = make_mock_ocr(["文字"])

        calls = []
        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            run_ocr("fake.mp4", str(tmp_path), ocr, progress_callback=lambda p, m: calls.append(p))

        assert 0 in calls   # 初始化时调用 0
        assert 100 in calls  # 完成时调用 100

    def test_timestamp_included(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frames = [(dummy_frame, "00:00:05", 50)]
        ocr = make_mock_ocr(["字幕内容"])

        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            result = run_ocr("fake.mp4", str(tmp_path), ocr, include_timestamp=True)

        assert "[00:00:05]" in result

    def test_timestamp_excluded(self, tmp_path):
        from core.pipeline import run_ocr

        dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        frames = [(dummy_frame, "00:00:05", 50)]
        ocr = make_mock_ocr(["字幕内容"])

        with patch("core.pipeline.VideoProcessor", return_value=make_mock_processor(frames)):
            result = run_ocr("fake.mp4", str(tmp_path), ocr, include_timestamp=False)

        assert "[" not in result
        assert "字幕内容" in result
