"""
Tests for LLMService module - using DeepSeek API.
"""
import json
import os
import pytest

from app.services.llm_service import LLMService, LLMServiceError
from app.config import get_settings


# Read DeepSeek API key from environment variable
# Priority: TEST_DEEPSEEK_API_KEY > DEEPSEEK_API_KEY
DEEPSEEK_API_KEY = os.getenv("TEST_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")


class TestLLMService:
    """Test cases for LLMService with real DeepSeek API."""

    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance with real API key."""
        settings = get_settings()
        # Temporarily override API key
        original_key = settings.DEEPSEEK_API_KEY
        settings.DEEPSEEK_API_KEY = DEEPSEEK_API_KEY or "sk-test-key"

        service = LLMService()
        yield service

        # Restore original key
        settings.DEEPSEEK_API_KEY = original_key

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEEPSEEK_API_KEY, reason="DeepSeek API key not available")
    async def test_call_api_basic(self, llm_service):
        """Test basic API call to DeepSeek."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, test!' and nothing else."}
        ]

        response = await llm_service.call_api(messages)
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"API Response: {response}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEEPSEEK_API_KEY, reason="DeepSeek API key not available")
    async def test_extract_fields_contract(self, llm_service):
        """Test extracting fields from contract text."""
        text = """
        合同编号：HT-2024-001
        甲方：ABC科技有限公司
        乙方：XYZ服务有限公司
        签订日期：2024年3月15日
        合同金额：¥100,000.00
        项目名称：软件开发项目
        """

        field_list = ["合同编号", "甲方", "乙方", "签订日期", "合同金额", "项目名称"]

        result = await llm_service.extract_fields(text, field_list)

        print(f"Extracted fields: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # Verify all fields are present
        for field in field_list:
            assert field in result

        # Verify some values
        assert "HT-2024-001" in str(result.get("合同编号", ""))
        assert "ABC科技有限公司" in str(result.get("甲方", ""))

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEEPSEEK_API_KEY, reason="DeepSeek API key not available")
    async def test_extract_fields_invoice(self, llm_service):
        """Test extracting fields from invoice text."""
        text = """
        发票号码：FP20240315001
        开票日期：2024年3月15日
        购买方：北京科技有限公司
        销售方：上海供应商有限公司
        金额：¥5,280.00
        税额：¥686.40
        价税合计：¥5,966.40
        """

        field_list = ["发票号码", "开票日期", "购买方", "销售方", "金额", "价税合计"]

        result = await llm_service.extract_fields(text, field_list)

        print(f"Extracted fields: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # Verify fields
        assert "发票号码" in result
        assert "开票日期" in result
        assert "北京科技有限公司" in str(result.get("购买方", ""))

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEEPSEEK_API_KEY, reason="DeepSeek API key not available")
    async def test_extract_fields_missing_fields(self, llm_service):
        """Test extracting fields when some are missing."""
        text = """
        合同编号：HT-2024-001
        甲方：ABC科技有限公司
        """

        field_list = ["合同编号", "甲方", "乙方", "签订日期"]

        result = await llm_service.extract_fields(text, field_list)

        # Known fields should be extracted
        assert "合同编号" in result
        assert "甲方" in result

        # Missing fields should be None or empty
        print(f"Result with missing fields: {json.dumps(result, ensure_ascii=False, indent=2)}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not DEEPSEEK_API_KEY, reason="DeepSeek API key not available")
    async def test_analyze_document_summary(self, llm_service):
        """Test document analysis - summary."""
        text = """
        这是一份关于人工智能技术在医疗领域应用的报告。
        报告首先介绍了人工智能的基本概念和发展历程，
        然后详细分析了AI在医学影像诊断、药物研发、个性化治疗等方面的应用案例。
        最后，报告讨论了AI医疗面临的挑战和未来发展趋势。
        """

        result = await llm_service.analyze_document(text, "summary")

        print(f"Analysis result: {json.dumps(result, ensure_ascii=False, indent=2)}")
        assert isinstance(result, dict)


class TestLLMServiceErrorHandling:
    """Error handling tests for LLMService."""

    def test_missing_api_key(self):
        """Test that service raises error when API key is missing."""
        # Temporarily override settings
        from app.config import get_settings
        settings = get_settings()
        original_key = settings.DEEPSEEK_API_KEY
        try:
            settings.DEEPSEEK_API_KEY = ""
            with pytest.raises(LLMServiceError) as exc_info:
                LLMService()
            assert "API key not configured" in str(exc_info.value)
        finally:
            settings.DEEPSEEK_API_KEY = original_key


class TestLLMServiceParseResponse:
    """Tests for parsing LLM responses."""

    @pytest.fixture
    def llm_service_with_key(self):
        """Create LLM service with mock key for parsing tests."""
        service = LLMService(api_key="sk-test-key")
        yield service

    def test_parse_json_response_plain(self, llm_service_with_key):
        """Test parsing plain JSON response."""
        response = '{"field1": "value1", "field2": "value2"}'
        result = llm_service_with_key._parse_json_response(response, ["field1", "field2"])

        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_parse_json_response_markdown(self, llm_service_with_key):
        """Test parsing JSON in markdown code block."""
        response = '''```json
        {"field1": "value1", "field2": "value2"}
        ```'''
        result = llm_service_with_key._parse_json_response(response, ["field1", "field2"])

        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_parse_json_response_with_extra_text(self, llm_service_with_key):
        """Test parsing JSON with extra text."""
        response = 'Here is the result:\n\n{"field1": "value1", "field2": "value2"}\n\nHope this helps!'
        result = llm_service_with_key._parse_json_response(response, ["field1", "field2"])

        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_parse_json_response_missing_fields(self, llm_service_with_key):
        """Test parsing JSON with missing expected fields."""
        response = '{"field1": "value1"}'
        result = llm_service_with_key._parse_json_response(response, ["field1", "field2"])

        assert result["field1"] == "value1"
        assert result["field2"] is None  # Missing field should be None

    def test_parse_json_response_invalid_json(self, llm_service_with_key):
        """Test parsing invalid JSON response."""
        response = "This is not JSON"

        with pytest.raises(LLMServiceError) as exc_info:
            llm_service_with_key._parse_json_response(response, ["field1"])

        assert "No JSON found" in str(exc_info.value) or "Failed to parse" in str(exc_info.value)