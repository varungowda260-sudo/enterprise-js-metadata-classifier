"""
JavaScript Metadata Parser - Robust Traversal Implementation

This parser extracts fields from JavaScript metadata files using a state-machine
tokenizer and proper bracket matching for maximum robustness.

Design Principles:
1. Never execute JavaScript - only read as UTF-8 text
2. Position-independent - fields can appear anywhere
3. Proper bracket matching for nested structures
4. Content-driven - searches by field name, not by structure
5. Configurable - additional fields can be extracted by configuration
"""
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator, Tuple
from dataclasses import dataclass
from models import MetadataRecord


# =============================================================================
# Tokenizer-Based Parser - Handles all formatting variations
# =============================================================================

class Token:
    """Token types for the tokenizer."""
    STRING = 'STRING'
    COLON = 'COLON'
    COMMA = 'COMMA'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    LBRACKET = 'LBRACKET'
    RBRACKET = 'RBRACKET'
    IDENTIFIER = 'IDENTIFIER'
    NUMBER = 'NUMBER'
    BOOLEAN = 'BOOLEAN'
    NULL = 'NULL'
    EOF = 'EOF'


@dataclass
class TokenInfo:
    """Information about a token."""
    type: str
    value: str
    position: int


def tokenize(content: str) -> Generator[TokenInfo, None, None]:
    """
    Tokenize JavaScript/JSON content into tokens.
    Handles both JSON and JavaScript object literal syntax.
    Yields TokenInfo objects for each token found.
    """
    pos = 0
    length = len(content)

    while pos < length:
        char = content[pos]

        # Skip whitespace
        if char in ' \t\n\r':
            pos += 1
            continue

        # String (double quotes)
        if char == '"':
            start = pos
            pos += 1
            while pos < length:
                if content[pos] == '\\':
                    pos += 2  # Skip escape sequence
                    continue
                if content[pos] == '"':
                    pos += 1
                    break
                pos += 1
            yield TokenInfo(Token.STRING, content[start:pos], start)
            continue

        # String (single quotes)
        if char == "'":
            start = pos
            pos += 1
            while pos < length:
                if content[pos] == '\\':
                    pos += 2
                    continue
                if content[pos] == "'":
                    pos += 1
                    break
                pos += 1
            yield TokenInfo(Token.STRING, content[start:pos], start)
            continue

        # Punctuation
        if char == ':':
            yield TokenInfo(Token.COLON, ':', pos)
            pos += 1
            continue

        if char == ',':
            yield TokenInfo(Token.COMMA, ',', pos)
            pos += 1
            continue

        if char == '{':
            yield TokenInfo(Token.LBRACE, '{', pos)
            pos += 1
            continue

        if char == '}':
            yield TokenInfo(Token.RBRACE, '}', pos)
            pos += 1
            continue

        if char == '[':
            yield TokenInfo(Token.LBRACKET, '[', pos)
            pos += 1
            continue

        if char == ']':
            yield TokenInfo(Token.RBRACKET, ']', pos)
            pos += 1
            continue

        # Identifier or keyword
        if char.isalpha() or char == '_' or char == '$':
            start = pos
            while pos < length and (content[pos].isalnum() or content[pos] in '_$'):
                pos += 1
            word = content[start:pos]
            if word in ('true', 'false'):
                yield TokenInfo(Token.BOOLEAN, word, start)
            elif word == 'null':
                yield TokenInfo(Token.NULL, word, start)
            else:
                yield TokenInfo(Token.IDENTIFIER, word, start)
            continue

        # Number
        if char.isdigit() or (char == '-' and pos + 1 < length and content[pos + 1].isdigit()):
            start = pos
            pos += 1
            while pos < length and (content[pos].isdigit() or content[pos] in '.eE+-'):
                pos += 1
            yield TokenInfo(Token.NUMBER, content[start:pos], start)
            continue

        # Skip unknown characters
        pos += 1

    yield TokenInfo(Token.EOF, '', pos)


def extract_string_value(token_value: str) -> str:
    """
    Extract the actual string value from a quoted string token.
    Handles escape sequences.
    """
    if len(token_value) < 2:
        return token_value

    # Remove quotes
    quote_char = token_value[0]
    if token_value[-1] == quote_char:
        inner = token_value[1:-1]
    else:
        inner = token_value[1:]

    # Handle common escape sequences
    result = inner.replace('\\"', '"')
    result = result.replace("\\'", "'")
    result = result.replace('\\\\', '\\')
    result = result.replace('\\n', '\n')
    result = result.replace('\\r', '\r')
    result = result.replace('\\t', '\t')

    return result


def find_name_value_in_object(tokens: List[TokenInfo], start_idx: int, end_idx: int) -> Generator[Tuple[str, str], None, None]:
    """
    Find name/value pairs within a single object (between braces).

    Handles the canonical format where each note_items entry is:
    {"name":"fieldname", "type":..., "value":["actual_value"]}

    Also handles reversed order where value comes before name.
    """
    # Scan for name and value within this object scope
    name_val = None
    value_val = None

    i = start_idx
    while i < end_idx:
        token = tokens[i]

        if token.type == Token.STRING or token.type == Token.IDENTIFIER:
            key = extract_string_value(token.value) if token.type == Token.STRING else token.value
            key_lower = key.lower()

            # Look for key: value pattern
            if i + 2 < len(tokens) and tokens[i + 1].type == Token.COLON:
                val_token = tokens[i + 2]

                if key_lower == 'name':
                    if val_token.type == Token.STRING:
                        name_val = extract_string_value(val_token.value)

                elif key_lower == 'value':
                    if val_token.type == Token.STRING:
                        value_val = extract_string_value(val_token.value)
                    elif val_token.type == Token.LBRACKET and i + 3 < len(tokens):
                        # Array value: ["something"]
                        if tokens[i + 3].type == Token.STRING:
                            value_val = extract_string_value(tokens[i + 3].value)
                        elif tokens[i + 3].type == Token.RBRACKET:
                            # Empty array
                            pass
        i += 1

    # If we found both name and value in this object, yield the pair
    if name_val is not None and value_val is not None:
        yield (name_val, value_val)


def find_all_objects_content(content: str) -> Generator[str, None, None]:
    """
    Find all JSON-like objects in the content and extract name/value pairs from each.
    Processes objects at ALL depths - not just the outermost, not just the innermost.
    Uses proper bracket matching for nested structures.
    """
    tokens = list(tokenize(content))

    # We need to find ALL complete objects at every depth level
    # An object is complete when we find a matching closing brace at the same depth

    depth = 0
    object_starts = []  # Stack of (depth, start_idx) for open braces

    for i, token in enumerate(tokens):
        if token.type == Token.LBRACE:
            object_starts.append((depth, i))
            depth += 1

        elif token.type == Token.RBRACE:
            if object_starts:
                start_depth, start_idx = object_starts.pop()
                depth -= 1

                # This completes an object from start_idx to i
                # Extract name/value pairs from this object
                for name, val in find_name_value_in_object(tokens, start_idx, i + 1):
                    yield (name, val)


def extract_top_level_field(content: str, field_name: str) -> Optional[str]:
    """
    Extract a top-level field value from metadata content.
    Looks for "field_name": "value" or field_name: "value" patterns.
    Uses tokenization for proper handling.
    """
    tokens = list(tokenize(content))

    for i in range(len(tokens) - 2):
        token = tokens[i]

        # Check for identifier or string matching field_name
        if token.type in (Token.STRING, Token.IDENTIFIER):
            key = extract_string_value(token.value) if token.type == Token.STRING else token.value

            if key.lower() == field_name.lower():
                # Check for colon
                if i + 1 < len(tokens) and tokens[i + 1].type == Token.COLON:
                    val_token = tokens[i + 2]

                    if val_token.type == Token.STRING:
                        return extract_string_value(val_token.value)
                    elif val_token.type == Token.LBRACKET and i + 3 < len(tokens):
                        # Array value with string
                        if tokens[i + 3].type == Token.STRING:
                            return extract_string_value(tokens[i + 3].value)

    return None


def extract_from_all_objects(content: str, field_name: str) -> Optional[str]:
    """
    Search all objects in the content for a field with the given name.
    Returns the first non-empty value found.
    """
    # First check top-level
    top_value = extract_top_level_field(content, field_name)
    if top_value:
        return top_value

    # Then search in all objects for name/value pairs
    for found_name, found_value in find_all_objects_content(content):
        if found_name.lower() == field_name.lower() and found_value:
            return found_value

    return None


# =============================================================================
# Public API - Simple functions for extracting fields
# =============================================================================

def extract_note_unid(content: str) -> Optional[str]:
    """
    Extract note_unid from the metadata content.
    note_unid is typically at the top level of the metadata object.
    """
    return extract_any_field(content, "note_unid")


def extract_sys_name(content: str) -> Optional[str]:
    """
    Extract sys_name from the metadata content.
    sys_name is in note_items objects, searched position-independently.
    """
    return extract_from_all_objects(content, "sys_name")


def extract_status(content: str) -> Optional[str]:
    """
    Extract status from the metadata content.
    status is in note_items objects, searched position-independently.
    """
    return extract_from_all_objects(content, "status")


def extract_any_field(content: str, field_name: str) -> Optional[str]:
    """
    Extract any named field from metadata content.
    This is for future extensibility - new fields can be extracted
    without changing the parser.

    Args:
        content: Full file content
        field_name: Name of field to extract

    Returns:
        Extracted value or None
    """
    # Try top-level first
    value = extract_top_level_field(content, field_name)
    if value:
        return value

    # Then search in objects
    return extract_from_all_objects(content, field_name)


def extract_multiple_fields(content: str, field_names: List[str]) -> Dict[str, Optional[str]]:
    """
    Extract multiple fields from metadata content.

    Args:
        content: Full file content
        field_names: List of field names to extract

    Returns:
        Dictionary mapping field names to extracted values (or None if not found)
    """
    results: Dict[str, Optional[str]] = {}
    for field_name in field_names:
        results[field_name] = extract_any_field(content, field_name)
    return results


# =============================================================================
# Main Parsing Functions
# =============================================================================

def parse_js_metadata_content(content: str, file_name: str = "unknown") -> MetadataRecord:
    """
    Parse JavaScript metadata content string and extract required fields.

    This function uses proper tokenization and bracket matching for
    maximum robustness against formatting variations.

    Args:
        content: The file content as string
        file_name: Virtual file name for tracking

    Returns:
        MetadataRecord with extracted data
    """
    errors: List[str] = []

    # Extract each field independently - position-independent search
    note_unid = extract_note_unid(content)
    sys_name = extract_sys_name(content)
    status = extract_status(content)
    cc_number = extract_any_field(content, "cc_number")
    go_live_date_production = extract_any_field(content, "imp_date")
    itqm_closure = extract_any_field(content, "sec7_itqm_date_hist")
    cqa_closure = extract_any_field(content, "sec7_cqa_date_hist")
    closure_date = itqm_closure or cqa_closure or ""

    # Track which fields are missing
    if not note_unid:
        errors.append("Missing note_unid")
    if not sys_name:
        errors.append("Missing sys_name")
    if not status:
        errors.append("Missing status")

    # Record is valid only if all required fields are present
    is_valid = bool(note_unid and sys_name and status)

    return MetadataRecord(
        note_unid=note_unid or "",
        sys_name=sys_name or "",
        status=status or "",
        file_name=file_name,
        cc_number=cc_number or "",
        go_live_date_production=go_live_date_production or "",
        closure_date=closure_date,
        is_valid=is_valid,
        parse_errors=errors
    )


def parse_js_metadata_file(file_path: Path) -> MetadataRecord:
    """
    Parse a JavaScript metadata file and extract required fields.
    Never executes JavaScript - only reads as UTF-8 text.

    Args:
        file_path: Path to the .js file

    Returns:
        MetadataRecord with extracted data
    """
    # Read file with fallback encodings
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            content = file_path.read_text(encoding='latin-1')
        except Exception as e:
            return MetadataRecord(
                note_unid="",
                sys_name="",
                status="",
                file_name=file_path.name,
                cc_number="",
               go_live_date_production="",
                closure_date="",
                is_valid=False,
                parse_errors=[f"Failed to read file: {str(e)}"]
            )
    except Exception as e:
        return MetadataRecord(
            note_unid="",
            sys_name="",
            status="",
            file_name=file_path.name,
            cc_number="",
            go_live_date_production="",
            closure_date="",
            is_valid=False,
            parse_errors=[f"Failed to read file: {str(e)}"]
        )

    return parse_js_metadata_content(content, file_path.name)
