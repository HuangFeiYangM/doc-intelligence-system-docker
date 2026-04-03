"""
LLM Service module for interacting with DeepSeek API.
"""
import json
import logging
import re
from typing import Dict, List, Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

# Configure logger
logger = logging.getLogger(__name__)

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
        self.settings = get_settings()
        self.api_key = api_key or self.settings.DEEPSEEK_API_KEY
        self.api_base = self.settings.DEEPSEEK_API_BASE
        self.model = self.settings.DEEPSEEK_MODEL
        self.max_tokens = self.settings.DEEPSEEK_MAX_TOKENS
        self.temperature = self.settings.DEEPSEEK_TEMPERATURE
        self.timeout = self.settings.DEEPSEEK_TIMEOUT

        if not self.api_key:
            logger.error("DeepSeek API key not configured")
            raise LLMServiceError("DeepSeek API key not configured")

        # Create reusable HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        logger.debug("LLMService initialized with connection pooling")

    async def close(self):
        """Close the HTTP client and release resources."""
        if self.client:
            await self.client.aclose()
            logger.debug("LLMService HTTP client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

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
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        logger.debug(f"Calling DeepSeek API with {len(messages)} messages")

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Safely extract content from response
            content = self._extract_content(data)
            logger.debug(f"API call successful, received {len(content)} characters")
            return content

        except httpx.HTTPStatusError as e:
            logger.error(f"API HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMServiceError(f"API HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.TimeoutException:
            logger.error(f"API timeout after {self.timeout} seconds")
            raise LLMServiceError(f"API timeout after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            raise LLMServiceError(f"API call failed: {str(e)}")

    def _extract_content(self, data: Dict[str, Any]) -> str:
        """Safely extract content from API response.

        Args:
            data: API response JSON

        Returns:
            Extracted content string

        Raises:
            LLMServiceError: If response structure is invalid
        """
        try:
            # Safe navigation through response structure
            if not isinstance(data, dict):
                raise LLMServiceError(f"Invalid API response type: {type(data)}")

            choices = data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise LLMServiceError("No choices in API response")

            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                raise LLMServiceError("Invalid choice format in API response")

            message = first_choice.get("message")
            if not isinstance(message, dict):
                raise LLMServiceError("No message in API response choice")

            content = message.get("content")
            if content is None:
                raise LLMServiceError("No content in API response message")

            return str(content)

        except LLMServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract content from response: {data}")
            raise LLMServiceError(f"Failed to parse API response: {str(e)}")

    async def extract_fields(self, text: str, field_list: List[str]) -> Dict[str, Any]:
        """Extract specified fields from text using LLM.

        Args:
            text: Document text content
            field_list: List of field names to extract

        Returns:
            Dictionary with extracted field values
        """
        logger.info(f"Extracting fields: {field_list}")

        # Truncate text if too long to avoid token limit
        max_text_length = 8000  # Conservative limit
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length] + "\n[Content truncated...]"

        fields_str = ", ".join(field_list)

        # Cache prompt to avoid rebuilding
        system_message = "You are a helpful data extraction assistant that returns only valid JSON."
        prompt_template = (
            "You are a data extraction assistant. Please extract the following fields from the provided text:\n\n"
            "Fields to extract: {fields}\n\n"
            "Text content:\n{text}\n\n"
            "Instructions:\n"
            "1. Extract the exact values for each field from the text\n"
            "2. Return ONLY a valid JSON object with field names as keys and extracted values\n"
            "3. If a field is not found, use null as the value\n"
            "4. Do not include any explanations or markdown formatting, only the JSON object\n\n"
            'Response format example: {{"field1": "value1", "field2": "value2", "field3": null}}\n\n'
            "Your response:"
        )
        prompt = prompt_template.format(fields=fields_str, text=text)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        try:
            logger.debug("Calling API for field extraction")
            response = await self.call_api(messages)
            result = self._parse_json_response(response, field_list)
            logger.info(f"Field extraction completed, found {len([v for v in result.values() if v is not None])} non-null fields")
            return result
        except LLMServiceError:
            raise
        except Exception as e:
            logger.error(f"Field extraction failed: {e}", exc_info=True)
            raise LLMServiceError(f"Field extraction failed: {str(e)}")

    def _parse_json_response(self, response: str, field_list: List[str]) -> Dict[str, Any]:
        """Parse JSON response from LLM.

        Args:
            response: Raw API response string
            field_list: Expected field names

        Returns:
            Parsed dictionary
        """
        logger.debug(f"Parsing JSON response for fields: {field_list}")

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        # Clean up the response
        response = response.strip()

        result = None
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from response: {response[:200]}")
                    raise LLMServiceError(f"Failed to parse LLM response as JSON: {str(e)}")
            else:
                logger.error(f"No JSON found in response: {response[:200]}")
                raise LLMServiceError(f"No JSON found in LLM response")

        # Validate result contains expected fields
        validated_result = {}
        for field in field_list:
            validated_result[field] = result.get(field)
            if field not in result:
                logger.warning(f"Expected field '{field}' not found in response")

        logger.debug(f"Parsed result: {validated_result}")
        return validated_result

    async def analyze_document(self, text: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """Analyze document content using LLM.

        Args:
            text: Document text content
            analysis_type: Type of analysis (summary, keywords, entities)

        Returns:
            Analysis results
        """
        logger.info(f"Analyzing document with type: {analysis_type}")

        # Truncate text if too long
        max_text_length = 8000
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length] + "\n[Content truncated...]"

        prompts = {
            "summary": "Provide a concise summary of the following document:",
            "keywords": "Extract the top 10 keywords from the following document:",
            "entities": "Extract named entities (people, organizations, locations) from the following document:",
        }

        prompt_template = prompts.get(analysis_type, prompts["summary"])
        if analysis_type not in prompts:
            logger.warning(f"Unknown analysis type: {analysis_type}, using default")

        prompt = f"""{prompt_template}

Text content:
{text}

Return the result as a JSON object with appropriate keys.
"""

        messages = [
            {"role": "system", "content": "You are a document analysis assistant."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.call_api(messages)
            result = self._parse_json_response(response, ["result"])
            logger.info(f"Document analysis completed for type: {analysis_type}")
            return result
        except Exception as e:
            logger.error(f"Document analysis failed: {e}", exc_info=True)
            raise
