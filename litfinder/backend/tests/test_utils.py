"""
Unit tests for app.utils module.
"""
import pytest
from app.utils import sanitize_filename


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    def test_empty_string(self):
        """Empty string should return 'export' as fallback."""
        assert sanitize_filename("") == "export"
        assert sanitize_filename(None) == "export"  # type: ignore

    def test_normal_filename(self):
        """Normal filenames with spaces should be converted to underscores."""
        assert sanitize_filename("Normal Collection") == "Normal_Collection"
        assert sanitize_filename("My Research Papers") == "My_Research_Papers"
        assert sanitize_filename("valid-name_123") == "valid-name_123"

    def test_control_characters(self):
        """Control characters (CR, LF, etc.) should be removed."""
        # Carriage return and line feed
        assert sanitize_filename("Collection\r\nName") == "CollectionName"
        # Tab character
        assert sanitize_filename("Collection\tName") == "Collection_Name"
        # Null byte
        assert sanitize_filename("Collection\x00Name") == "CollectionName"
        # DEL character
        assert sanitize_filename("Collection\x7fName") == "CollectionName"

    def test_header_injection_characters(self):
        """Characters that could cause header injection should be removed."""
        # Quotes
        assert sanitize_filename('Collection"Name') == "CollectionName"
        assert sanitize_filename("Collection'Name") == "CollectionName"
        # Semicolons
        assert sanitize_filename("Collection;Name") == "CollectionName"
        # Equals
        assert sanitize_filename("Collection=Name") == "CollectionName"
        # Combined attack
        assert sanitize_filename('Collection"; Set-Cookie: evil=true') == "Collection_Set-Cookie_eviltrue"

    def test_path_traversal_characters(self):
        """Forward slashes and backslashes should be replaced with underscores."""
        # Forward slashes
        assert sanitize_filename("../../etc/passwd") == ".._.._etc_passwd"
        assert sanitize_filename("/etc/passwd") == "etc_passwd"
        # Backslashes
        assert sanitize_filename("..\\..\\Windows\\System32") == ".._..._Windows_System32"
        # Mixed
        assert sanitize_filename("path/to/../sensitive") == "path_to_..._sensitive"

    def test_special_characters(self):
        """Special filesystem characters should be replaced with underscores."""
        assert sanitize_filename("Collection<Name>") == "Collection_Name_"
        assert sanitize_filename("Collection:Name") == "Collection_Name"
        assert sanitize_filename("Collection|Name") == "Collection_Name"
        assert sanitize_filename("Collection?Name") == "Collection_Name"
        assert sanitize_filename("Collection*Name") == "Collection_Name"

    def test_multiple_spaces_collapsed(self):
        """Multiple spaces/underscores should be collapsed to single underscore."""
        assert sanitize_filename("Collection    Name") == "Collection_Name"
        assert sanitize_filename("Collection___Name") == "Collection_Name"
        assert sanitize_filename("Collection  _  Name") == "Collection_Name"

    def test_leading_trailing_underscores_removed(self):
        """Leading and trailing underscores should be removed."""
        assert sanitize_filename("_Collection_") == "Collection"
        assert sanitize_filename("___Collection___") == "Collection"
        assert sanitize_filename("/Collection/") == "Collection"

    def test_long_filenames(self):
        """Filenames longer than max_length should be truncated."""
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 200
        assert result == "a" * 200

    def test_custom_max_length(self):
        """Custom max_length parameter should be respected."""
        long_name = "a" * 100
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) == 50

    def test_max_length_with_trailing_underscore(self):
        """Truncation should remove trailing underscores."""
        # Create a name that ends with underscore after truncation
        long_name = "a" * 199 + "_" + "b" * 10
        result = sanitize_filename(long_name, max_length=200)
        assert len(result) <= 200
        assert not result.endswith("_")

    def test_all_characters_removed(self):
        """If all characters are removed, should return 'export'."""
        assert sanitize_filename("!!!") == "export"
        assert sanitize_filename("\"\"\"") == "export"
        assert sanitize_filename("///") == "export"
        assert sanitize_filename("\r\n\t") == "export"

    def test_cyrillic_characters_preserved(self):
        """Non-ASCII characters like Cyrillic should be preserved."""
        assert sanitize_filename("Применение машинного обучения") == "Применение_машинного_обучения"
        assert sanitize_filename("Иванов И. О.") == "Иванов_И._О."

    def test_real_world_attacks(self):
        """Test real-world attack vectors."""
        # SQL injection attempt
        assert sanitize_filename("Collection'; DROP TABLE users--") == "Collection_DROP_TABLE_users--"
        # Path traversal
        assert sanitize_filename("../../../root/.ssh/id_rsa") == ".._.._..._root_.ssh_id_rsa"
        # Header injection
        assert sanitize_filename("Evil\r\nSet-Cookie: admin=true") == "EvilSet-Cookie_admintrue"
        # Multiple exploits
        assert sanitize_filename("../../etc/passwd\r\nX-Evil: true") == ".._.._etc_passwdX-Evil_true"

    def test_edge_cases(self):
        """Test edge cases and corner cases."""
        # Single character
        assert sanitize_filename("a") == "a"
        # Only spaces
        assert sanitize_filename("   ") == "export"
        # Only underscores
        assert sanitize_filename("___") == "export"
        # Mixed valid and invalid
        assert sanitize_filename("Valid_123-name.txt") == "Valid_123-name.txt"
