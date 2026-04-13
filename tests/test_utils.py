from core.utils import text_similarity, is_duplicate, clean_text


class TestTextSimilarity:
    def test_identical(self):
        assert text_similarity("你好世界", "你好世界") == 1.0

    def test_empty(self):
        assert text_similarity("", "") == 1.0

    def test_completely_different(self):
        assert text_similarity("abc", "xyz") == 0.0

    def test_partial(self):
        ratio = text_similarity("你好世界", "你好")
        assert 0 < ratio < 1


class TestIsDuplicate:
    def test_exact_match(self):
        assert is_duplicate("hello", ["hello"], threshold=0.7)

    def test_similar_above_threshold(self):
        # "你好世界" vs "你好世界！" — 高度相似
        assert is_duplicate("你好世界", ["你好世界！"], threshold=0.7)

    def test_similar_below_threshold(self):
        assert not is_duplicate("完全不同的内容", ["你好世界"], threshold=0.7)

    def test_substring_containment(self):
        # text 被 old 包含，且长度差 < 5
        assert is_duplicate("你好", ["你好啊"], threshold=0.99)

    def test_empty_history(self):
        assert not is_duplicate("hello", [], threshold=0.7)

    def test_not_duplicate_when_different(self):
        assert not is_duplicate("第一集", ["第二集", "第三集"], threshold=0.7)


class TestCleanText:
    def test_strips_whitespace(self):
        assert clean_text("  hello  ") == "hello"

    def test_empty(self):
        assert clean_text("") == ""

    def test_no_change(self):
        assert clean_text("你好") == "你好"
