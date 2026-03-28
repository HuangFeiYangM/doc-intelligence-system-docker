"""
Validation utilities.
"""
import re
from typing import Any, Dict, List


def validate_field_mapping(mapping: Dict[str, str]) -> bool:
    """Validate field mapping configuration.

    Args:
        mapping: Field to cell address mapping

    Returns:
        True if valid

    Raises:
        ValueError: If mapping is invalid
    """
    if not isinstance(mapping, dict):
        raise ValueError("Field mapping must be a dictionary")

    # Excel cell address pattern (e.g., A1, B12, AA100)
    cell_pattern = re.compile(r'^[A-Z]+\d+$')

    for field, cell in mapping.items():
        if not isinstance(field, str) or not field.strip():
            raise ValueError(f"Field name must be a non-empty string: {field}")

        if not isinstance(cell, str) or not cell_pattern.match(cell.upper()):
            raise ValueError(f"Invalid cell address '{cell}' for field '{field}'")

    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove unsafe characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path separators and other unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > 200:
        name, ext = filename[:200].rsplit('.', 1)
        filename = f"{name}.{ext}"

    return filename


def validate_extracted_data(data: Dict[str, Any], expected_fields: List[str]) -> Dict[str, Any]:
    """Validate and normalize extracted data.

    Args:
        data: Extracted data dictionary
        expected_fields: List of expected field names

    Returns:
        Validated data dictionary
    """
    validated = {}
    for field in expected_fields:
        value = data.get(field)
        # Convert None or empty string to empty string
        if value is None or (isinstance(value, str) and not value.strip()):
            validated[field] = ""
        else:
            validated[field] = str(value)

    return validated
