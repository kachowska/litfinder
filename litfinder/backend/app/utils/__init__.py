"""
Utils package - shared utility functions.
"""
import re


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    r"""
    Sanitize filename for use in Content-Disposition header.

    Removes dangerous characters that could lead to header injection:
    - Control characters (CR, LF, etc.)
    - Quotes (", ')
    - Semicolons (;)
    - Backslashes (\) and forward slashes (/)
    - Other special characters that could break header syntax

    Args:
        filename: User-controlled filename string
        max_length: Maximum allowed length

    Returns:
        Sanitized filename safe for HTTP headers

    Examples:
        >>> sanitize_filename("Normal Collection")
        'Normal_Collection'
        >>> sanitize_filename("../../etc/passwd")
        '.._.._etc_passwd'
        >>> sanitize_filename("")
        'export'
        >>> sanitize_filename("a" * 300)[:10]
        'aaaaaaaaaa'
    """
    if not filename:
        return "export"

    # Remove control characters (including CR, LF)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

    # Remove quotes, semicolons, backslashes, equals
    filename = re.sub(r'["\';\\=]', '', filename)

    # Replace other potentially dangerous characters with underscores
    # Including forward slashes to prevent path traversal
    filename = re.sub(r'[<>:|?*/]', '_', filename)

    # Collapse multiple spaces/underscores
    filename = re.sub(r'[\s_]+', '_', filename)

    # Remove leading/trailing underscores
    filename = filename.strip('_')

    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('_')

    # Fallback if sanitization removed everything
    return filename if filename else "export"


__all__ = ['sanitize_filename']
