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

    async def extract_fields_list(self, text: str, field_list: List[str]) -> List[Dict[str, Any]]:
        """Extract list of records with specified fields from text using LLM.

        This method is designed for extracting multiple records (e.g., multiple persons)
        from a document. It returns a list of dictionaries, where each dictionary
        represents one record.

        Args:
            text: Document text content
            field_list: List of field names to extract for each record

        Returns:
            List of dictionaries, each containing field values for one record
        """
        logger.info(f"Extracting list of records with fields: {field_list}")

        # Truncate text if too long to avoid token limit
        max_text_length = 8000
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length] + "\n[Content truncated...]"

        fields_str = ", ".join(field_list)

        system_message = "You are a helpful data extraction assistant that returns only valid JSON. ALWAYS return a JSON array, even for a single record."
        prompt_template = (
            "You are a data extraction assistant. Please extract PERSON records with the following fields from the provided text.\n"
            "The document may contain MULTIPLE people (e.g., multiple developers, team members).\n"
            "CRITICAL: You MUST return a JSON ARRAY (start with [ and end with ]), even if there is only ONE person.\n\n"
            "Fields to extract for EACH person: {fields}\n\n"
            "Text content:\n{text}\n\n"
            "CRITICAL RULES - READ CAREFULLY:\n"
            "1. EACH person gets their OWN separate JSON object in the array\n"
            "2. If you see '黄飞扬：后端开发...' and '谷强：前端开发...', create TWO records:\n"
            "   [{{'姓名': '黄飞扬', '职位': '后端开发工程师', ...}}, {{'姓名': '谷强', '职位': '前端开发工程师', ...}}]\n"
            "3. NEVER put two names in different fields of the same object - that's WRONG\n"
            "4. WRONG example (NEVER DO THIS): {{'姓名': '黄飞扬', '人员姓名': '谷强'}}\n"
            "5. CORRECT: Create separate objects for each person\n"
            "6. Use EXACTLY the same field names for every person record\n\n"
            "PERSON IDENTIFICATION:\n"
            "- Look for sections like '主要参加人员', '开发者', '人员分工', '团队成员'\n"
            "- Each person usually has their own paragraph starting with their name\n"
            "- Common patterns: '姓名：描述' or '姓名 - 职位' or '姓名：任务'\n\n"
            "RETURN FORMAT:\n"
            "1. MUST be a JSON ARRAY starting with [ and ending with ]\n"
            "2. Each object in the array is ONE person with the SAME field names\n"
            "3. If only one person: [{{'姓名': '张三', '职位': '工程师', ...}}]\n"
            "4. If two people: [{{'姓名': '张三', ...}}, {{'姓名': '李四', ...}}]\n"
            "5. Use null for missing fields, but still include the field name\n"
            "6. Do NOT use markdown, do NOT add explanations\n\n"
            "CORRECT examples:\n"
            "Two people:  [{{'姓名': '黄飞扬', '职位': '后端开发', '任务': '架构设计'}}, {{'姓名': '谷强', '职位': '前端开发', '任务': 'UI设计'}}]\n"
            "One person:  [{{'姓名': '张三', '职位': '工程师', '任务': '开发'}}]\n"
            "No people:   []\n\n"
            "Your JSON response (array format):"
        )
        prompt = prompt_template.format(fields=fields_str, text=text)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        try:
            logger.debug("Calling API for list field extraction")
            response = await self.call_api(messages)
            result = self._parse_json_list_response(response, field_list)
            logger.info(f"List extraction completed, found {len(result)} records")
            return result
        except LLMServiceError:
            raise
        except Exception as e:
            logger.error(f"List field extraction failed: {e}", exc_info=True)
            raise LLMServiceError(f"List field extraction failed: {str(e)}")

    async def extract_fields_list_with_mapping(
        self,
        text: str,
        field_mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Extract list of records using exact field names from template mapping.

        This method tells LLM the exact field names to use, eliminating the need
        for fuzzy matching later.

        Args:
            text: Document text content
            field_mapping: Template field mapping dict (field_name -> cell_address)

        Returns:
            List of dictionaries with exact field names from template
        """
        # Get unique field names from mapping
        field_names = list(dict.fromkeys(field_mapping.keys()))
        logger.info(f"Extracting with exact field names: {field_names}")

        # Truncate text if too long
        max_text_length = 8000
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length] + "\n[Content truncated...]"

        fields_str = ", ".join(field_names)

        system_message = "You are a helpful data extraction assistant that returns only valid JSON."
        prompt_template = (
            "You are a data extraction assistant. Please extract person records from the provided text.\n"
            "The document may contain MULTIPLE people (e.g., multiple developers, team members).\n\n"
            "CRITICAL: Use EXACTLY these field names in your response (do not change them):\n"
            "{fields}\n\n"
            "Text content:\n{text}\n\n"
            "INSTRUCTIONS:\n"
            "1. Identify ALL separate people in the text\n"
            "2. For each person, create a JSON object using EXACTLY the field names listed above\n"
            "3. If a field doesn't apply to a person, use null as the value\n"
            "4. Return a JSON ARRAY with one object per person\n"
            "5. Use the EXACT field names provided - do not create your own\n"
            "6. Do NOT combine multiple people into one record\n"
            "7. Do NOT use markdown, do NOT add explanations\n\n"
            "Example with fields '姓名,职位,任务':\n"
            "[{{'姓名': '张三', '职位': '工程师', '任务': '后端开发'}}, {{'姓名': '李四', '职位': '设计师', '任务': 'UI设计'}}]\n\n"
            "Your JSON response (use exact field names: {fields}):"
        )
        prompt = prompt_template.format(fields=fields_str, text=text)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        try:
            logger.debug("Calling API with exact field mapping")
            response = await self.call_api(messages)
            result = self._parse_json_list_response_with_mapping(response, field_names)
            logger.info(f"Extraction completed with exact fields, found {len(result)} records")
            return result
        except LLMServiceError:
            raise
        except Exception as e:
            logger.error(f"Field extraction with mapping failed: {e}", exc_info=True)
            raise LLMServiceError(f"Field extraction with mapping failed: {str(e)}")

    def _parse_json_list_response_with_mapping(
        self,
        response: str,
        expected_fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Parse JSON response ensuring exact field names from template.

        Args:
            response: Raw API response
            expected_fields: Exact field names from template

        Returns:
            List of dictionaries with exact field names
        """
        logger.debug(f"Parsing with expected fields: {expected_fields}")

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)

        response = response.strip()

        # Parse JSON
        result = None
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = self._extract_json_with_balanced_brackets(response)

        if result is None:
            raise LLMServiceError("Failed to parse LLM response as JSON")

        # Ensure it's a list
        if not isinstance(result, list):
            if isinstance(result, dict):
                result = [result]
            else:
                result = []

        # Normalize each record to have exact field names
        normalized_results = []
        for record in result:
            if not isinstance(record, dict):
                continue

            normalized = {}
            for field in expected_fields:
                # Try exact match first
                if field in record:
                    normalized[field] = record[field]
                else:
                    # Try case-insensitive match
                    field_lower = field.lower()
                    matched = False
                    for key, value in record.items():
                        if key.lower() == field_lower:
                            normalized[field] = value
                            matched = True
                            break
                    if not matched:
                        normalized[field] = None
                        logger.warning(f"Field '{field}' not found in LLM response")

            normalized_results.append(normalized)

        logger.debug(f"Normalized {len(normalized_results)} records with exact fields")
        return normalized_results

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

    def _parse_json_list_response(self, response: str, field_list: List[str]) -> List[Dict[str, Any]]:
        """Parse JSON array response from LLM for list extraction.

        Args:
            response: Raw API response string
            field_list: Expected field names for each record

        Returns:
            List of parsed dictionaries
        """
        logger.debug(f"Parsing JSON list response for fields: {field_list}")
        logger.debug(f"Raw response: {response[:1000]}...")

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
            logger.debug(f"Extracted from markdown code block")

        # Clean up the response
        response = response.strip()
        logger.debug(f"Cleaned response: {response[:1000]}...")

        result = None
        try:
            result = json.loads(response)
            logger.debug(f"Successfully parsed JSON directly")
        except json.JSONDecodeError as e1:
            logger.debug(f"Direct JSON parse failed: {e1}, trying to extract JSON...")

            # Strategy: find the outermost brackets or braces
            # First, try to find a JSON array by matching balanced brackets
            result = self._extract_json_with_balanced_brackets(response)

            if result is None:
                logger.error(f"Failed to extract valid JSON from response: {response[:1000]}")
                raise LLMServiceError(f"Failed to parse LLM response as JSON: {str(e1)}")

        # Ensure result is a list
        if not isinstance(result, list):
            logger.warning(f"Expected list but got {type(result).__name__}, wrapping in list")
            if isinstance(result, dict):
                result = [result]
            else:
                result = []

        # Ensure result is a list
        if not isinstance(result, list):
            logger.warning(f"Expected list but got {type(result).__name__}, wrapping in list")
            if isinstance(result, dict):
                result = [result]
            else:
                result = []

        # Validate each record contains expected fields
        validated_results = []
        for idx, record in enumerate(result):
            if not isinstance(record, dict):
                logger.warning(f"Record {idx} is not a dict, skipping: {record}")
                continue
            validated_record = {}
            for field in field_list:
                validated_record[field] = record.get(field)
                if field not in record:
                    logger.warning(f"Expected field '{field}' not found in record {idx}")
            validated_results.append(validated_record)

        logger.info(f"Parsed {len(validated_results)} valid records from LLM response")
        return validated_results

    def _extract_json_with_balanced_brackets(self, text: str):
        """Extract JSON by finding balanced brackets or braces.

        This method properly handles nested structures by counting brackets.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON object/list or None if extraction fails
        """
        text = text.strip()

        # Try to find an array first (starts with [)
        for start_char, end_char in [('[', ']'), ('{', '}')]:
            start_idx = text.find(start_char)
            if start_idx == -1:
                continue

            # Find the matching closing bracket by counting
            count = 0
            end_idx = -1
            for i in range(start_idx, len(text)):
                if text[i] == start_char:
                    count += 1
                elif text[i] == end_char:
                    count -= 1
                    if count == 0:
                        end_idx = i
                        break

            if end_idx != -1:
                json_str = text[start_idx:end_idx + 1]
                try:
                    result = json.loads(json_str)
                    logger.debug(f"Successfully extracted JSON using balanced {start_char}{end_char}")
                    return result
                except json.JSONDecodeError:
                    logger.debug(f"Failed to parse extracted {start_char}...{end_char} as JSON")
                    continue

        return None

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
