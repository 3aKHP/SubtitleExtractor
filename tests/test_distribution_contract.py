from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_default_requirements_keep_asr_optional():
    requirements = read("requirements.txt").lower()
    optional_asr = read("requirements-asr.txt").lower()

    assert "faster-whisper" not in requirements
    assert "ctranslate2" not in requirements
    assert "rapidocr" not in requirements
    assert "onnxruntime" not in requirements
    assert "faster-whisper" in optional_asr
    assert "ctranslate2" in optional_asr


def test_windows_entrypoints_do_not_pin_local_python_env():
    pinned_python = r"envs\subtitle-extractor\python.exe".lower()
    local_drive = r"E:\Anaconda3".lower()

    for path in ("setup_env.bat", "setup_asr_cuda.bat", "start.bat"):
        content = read(path).lower()
        assert pinned_python not in content
        assert local_drive not in content
        assert "subtitle_extractor_env" in content


def test_readme_uses_clone_friendly_commands():
    readme = read("README.md")

    assert r"E:\Anaconda3\envs\subtitle-extractor\python.exe" not in readme
    assert "conda run -n subtitle-extractor python app/server.py" in readme
    assert "conda run -n subtitle-extractor python scripts/smoke_server.py" in readme
    assert "docs/release_checklist.md" in readme
    assert "docs/release_audit.md" in readme
    assert "CHANGELOG.md" in readme
    assert ".\\setup_env.bat" in readme


def test_runtime_smoke_script_exists():
    assert (ROOT / "scripts" / "smoke_server.py").exists()


def test_release_checklist_exists():
    checklist = read("docs/release_checklist.md")

    assert "Required baseline: OK" in checklist
    assert "core.asr_worker" in checklist
    assert "app/ffmpeg.exe" in checklist
    assert "Git LFS is not required" in checklist
    assert "RapidOCR is not part of the supported distribution path" in checklist
    assert "docs/release_audit.md" in checklist


def test_release_audit_exists():
    audit = read("docs/release_audit.md")

    assert "PaddleOCR CPU" in audit
    assert "ASR native dependency isolation" in audit
    assert "92 passed" in audit
    assert "Remaining Release Actions" in audit


def test_dangerous_local_cleanup_script_is_not_tracked_content():
    assert not (ROOT / "clean_env.py").exists()
    assert "clean_env.py" in read(".gitignore")


def test_jieba_is_installed_dependency_not_vendored():
    readme = read("README.md")

    assert not (ROOT / "app" / "jieba").exists()
    assert "Git LFS" not in readme
    assert "jieba" in read("requirements.txt")


def test_changelog_exists_for_public_release():
    changelog = read("CHANGELOG.md")

    assert "PaddleOCR CPU" in changelog
    assert "optional ASR" in changelog
    assert "Git LFS" in changelog
