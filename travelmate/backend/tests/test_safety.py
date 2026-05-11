from __future__ import annotations

import pytest
from app.utils.safety import (
    input_safety_check,
    output_safety_check,
    check_rate_limit,
)


class TestInputSafety:
    def test_block_keyword(self):
        result = input_safety_check("怎么逃票进去")
        assert result["passed"] is False
        assert result["level"] == "BLOCK"

    def test_warn_keyword(self):
        result = input_safety_check("我想一个人去偏远地区旅行")
        assert result["passed"] is True
        assert result["level"] == "WARN"
        assert "偏远地区" in result.get("warning", "")

    def test_urgent_keyword(self):
        result = input_safety_check("我高原反应了怎么办")
        assert result["passed"] is True
        assert result["level"] == "URGENT"
        assert "120" in result.get("warning", "")

    def test_safe_message(self):
        result = input_safety_check("杭州有什么好玩的")
        assert result["passed"] is True
        assert result["level"] == "SAFE"


class TestOutputSafety:
    def test_dangerous_output_blocked(self):
        result = output_safety_check("建议你去翻越围栏")
        assert result["passed"] is False

    def test_safe_output_passes(self):
        result = output_safety_check("西湖是一个美丽的景点")
        assert result["passed"] is True


class TestRateLimit:
    def test_allows_first_request(self):
        assert check_rate_limit("test_ratelimit", max_requests=3) is True

    def test_blocks_after_limit(self):
        device = "test_ratelimit_over"
        for _ in range(3):
            check_rate_limit(device, max_requests=3)
        assert check_rate_limit(device, max_requests=3) is False
