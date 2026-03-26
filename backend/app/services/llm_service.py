"""
LLM Service module for interacting with DeepSeek API.
"""
import json
import re
from typing import Dict, List, Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()


class LLMServiceError(Exception):
    """Exception raised for LLM service errors."""
    pass


class LLMService:
    """Service for interacting with DeepSeek LLM API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM service.

        Args:
            api_key: Optional API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.api_base = settings.DEEPSEEK_API_BASE
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.temperature = settings.DEEPSEEK_TEMPERATURE
        self.timeout = settings.DEEPSEEK_TIMEOUT

        if not self.api_key:
            raise LLMServiceError("DeepSeek API key not configured")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def call_api(self, messages: List[Dict[str, str]]) -> str:
        """Call DeepSeek API with retry mechanism.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            API response content

        Raises:
            LLMServiceError: If API call fails after retries
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        async with httpx.AsyncClient(timeout=self.timeout, proxies={}) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                raise LLMServiceError(f"API HTTP error: {e.response.status_code} - {e.response.text}")
            except httpx.TimeoutException:
                raise LLMServiceError(f"API timeout after {self.timeout} seconds")
            except Exception as e:
                raise LLMServiceError(f"API call failed: {str(e)}")

    async def extract_fields(self, text: str, field_list: List[str]) -> Dict[str, Any]:
        """Extract specified fields from text using LLM.

        Args:
            text: Document text content
            field_list: List of field names to extract

        Returns:
            Dictionary with extracted field values
        """
        fields_str = ", ".join(field_list)

        prompt = f"""You are a data extraction assistant. Please extract the following fields from the provided text:

Fields to extract: {fields_str}

Text content:
{text}

Instructions:
1. Extract the exact values for each field from the text
2. Return ONLY a valid JSON object with field names as keys and extracted values
3. If a field is not found, use null as the value
4. Do not include any explanations or markdown formatting, only the JSON object

Response format example:
{{"field1": "value1", "field2": "value2", "field3": null}}

Your response:"""

        messages = [
            {"role": "system", "content": "You are a helpful data extraction assistant that returns only valid JSON."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.call_api(messages)
            return self._parse_json_response(response, field_list)
        except Exception as e:
            raise LLMServiceError(f"Field extraction failed: {str(e)}")

    def _parse_json_response(self, response: str, field_list: List[str]) -> Dict[str, Any]:
        """Parse JSON response from LLM.

        Args:
            response: Raw API response string
            field_list: Expected field names

        Returns:
            Parsed dictionary
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        # Clean up the response
        response = response.strip()

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    raise LLMServiceError(f"Failed to parse LLM response as JSON: {response}")
            else:
                raise LLMServiceError(f"No JSON found in LLM response: {response}")

        # Validate result contains expected fields
        validated_result = {}
        for field in field_list:
            validated_result[field] = result.get(field)

        return validated_result

    async def analyze_document(self, text: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """Analyze document content using LLM.

        Args:
            text: Document text content
            analysis_type: Type of analysis (summary, keywords, entities)

        Returns:
            Analysis results
        """
        prompts = {
            "summary": "Provide a concise summary of the following document:",
            "keywords": "Extract the top 10 keywords from the following document:",
            "entities": "Extract named entities (people, organizations, locations) from the following document:",
        }

        prompt_template = prompts.get(analysis_type, prompts["summary"])

        prompt = f"""{prompt_template}

Text content:
{text}

Return the result as a JSON object with appropriate keys.
"""

        messages = [
            {"role": "system", "content": "You are a document analysis assistant."},
            {"role": "user", "content": prompt}
        ]

        response = await self.call_api(messages)
        return self._parse_json_response(response, ["result"])
