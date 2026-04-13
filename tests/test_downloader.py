import os
import pytest
from unittest.mock import patch, MagicMock
from core.downloader import get_video_metadata, download_video


class TestGetVideoMetadata:
    def test_returns_parsed_json(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ('{"title": "测试视频", "id": "BV123"}', "")

        with patch("core.downloader.subprocess.Popen", return_value=mock_proc):
            result = get_video_metadata("https://www.bilibili.com/video/BV123")

        assert result["title"] == "测试视频"
        assert result["id"] == "BV123"

    def test_raises_on_nonzero_returncode(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "网络错误")

        with patch("core.downloader.subprocess.Popen", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="获取元数据失败"):
                get_video_metadata("https://www.bilibili.com/video/BV123")

    def test_raises_on_invalid_json(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("not json", "")

        with patch("core.downloader.subprocess.Popen", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="无法解析"):
                get_video_metadata("https://www.bilibili.com/video/BV123")

    def test_command_includes_user_agent(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ('{"title":"t","id":"1"}', "")

        with patch("core.downloader.subprocess.Popen", return_value=mock_proc) as mock_popen:
            get_video_metadata("https://www.bilibili.com/video/BV1")
            cmd = mock_popen.call_args[0][0]
            assert "--user-agent" in cmd
            assert "TestAgent/1.0" in cmd


class TestDownloadVideo:
    def test_success(self, tmp_path):
        save_path = str(tmp_path / "video.mp4")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = ("", "")

        # 模拟文件被创建
        with patch("core.downloader.subprocess.Popen", return_value=mock_proc):
            with patch("os.path.exists", return_value=True):
                download_video("https://www.bilibili.com/video/BV1", save_path)

    def test_raises_when_file_missing_after_failure(self, tmp_path):
        save_path = str(tmp_path / "video.mp4")
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = ("", "下载失败")

        with patch("core.downloader.subprocess.Popen", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="下载失败"):
                download_video("https://www.bilibili.com/video/BV1", save_path)
