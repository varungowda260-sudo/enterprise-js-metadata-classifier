#!/usr/bin/env python3
"""
Comprehensive Unit Tests for JavaScript Metadata Parser

Tests cover:
- Field at various positions (beginning, middle, end)
- Missing field scenarios
- Duplicate fields
- Unknown/extra metadata fields
- Formatting variations
- Nested structures
- Edge cases
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from parser import (
    parse_js_metadata_content,
    extract_note_unid,
    extract_sys_name,
    extract_status,
    extract_any_field,
    extract_multiple_fields,
)


def test_result(name: str, expected: dict, actual: dict) -> bool:
    """Compare expected vs actual and print result."""
    passed = (
        actual['note_unid'] == expected['note_unid'] and
        actual['sys_name'] == expected['sys_name'] and
        actual['status'] == expected['status'] and
        actual['is_valid'] == expected['is_valid']
    )

    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")

    if not passed:
        print(f"         Expected: {expected}")
        print(f"         Got:      {actual}")

    return passed


def run_tests():
    """Run all parser tests."""
    total = 0
    passed = 0

    print("=" * 60)
    print("PARSER ROBUSTNESS TEST SUITE")
    print("=" * 60)

    # =========================================================================
    # TEST: sys_name near the beginning
    # =========================================================================
    print("\n[TEST] sys_name near the beginning of note_items")
    total += 1
    content = '''{"note_unid":"TEST001","note_items":[{"name":"sys_name","value":["SAP"]},{"name":"other1","value":["x"]},{"name":"other2","value":["y"]},{"name":"status","value":["Open"]}]}'''
    result = parse_js_metadata_content(content, "test1.js")
    if test_result("sys_name at beginning",
        {'note_unid': 'TEST001', 'sys_name': 'SAP', 'status': 'Open', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: sys_name near the end
    # =========================================================================
    print("\n[TEST] sys_name near the end of note_items")
    total += 1
    content = '''{"note_unid":"TEST002","note_items":[{"name":"field1","value":["a"]},{"name":"field2","value":["b"]},{"name":"field3","value":["c"]},{"name":"field4","value":["d"]},{"name":"status","value":["Closed"]},{"name":"sys_name","value":["Oracle"]}]}'''
    result = parse_js_metadata_content(content, "test2.js")
    if test_result("sys_name at end",
        {'note_unid': 'TEST002', 'sys_name': 'Oracle', 'status': 'Closed', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: status near the beginning
    # =========================================================================
    print("\n[TEST] status near the beginning of note_items")
    total += 1
    content = '''{"note_unid":"TEST003","note_items":[{"name":"status","value":["Active"]},{"name":"sys_name","value":["MySQL"]}]}'''
    result = parse_js_metadata_content(content, "test3.js")
    if test_result("status at beginning",
        {'note_unid': 'TEST003', 'sys_name': 'MySQL', 'status': 'Active', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: status near the end
    # =========================================================================
    print("\n[TEST] status near the end of note_items")
    total += 1
    content = '''{"note_unid":"TEST004","note_items":[{"name":"sys_name","value":["PostgreSQL"]},{"name":"field1","value":["x"]},{"name":"field2","value":["y"]},{"name":"status","value":["Ready"]}]}'''
    result = parse_js_metadata_content(content, "test4.js")
    if test_result("status at end",
        {'note_unid': 'TEST004', 'sys_name': 'PostgreSQL', 'status': 'Ready', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: missing sys_name
    # =========================================================================
    print("\n[TEST] missing sys_name")
    total += 1
    content = '''{"note_unid":"TEST005","note_items":[{"name":"status","value":["Open"]}]}'''
    result = parse_js_metadata_content(content, "test5.js")
    if test_result("missing sys_name",
        {'note_unid': 'TEST005', 'sys_name': '', 'status': 'Open', 'is_valid': False},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # Check error message
    if "Missing sys_name" in result.parse_errors:
        print("  [PASS] Correct error: 'Missing sys_name'")
    else:
        print(f"  [FAIL] Expected 'Missing sys_name' error, got: {result.parse_errors}")

    # =========================================================================
    # TEST: missing status
    # =========================================================================
    print("\n[TEST] missing status")
    total += 1
    content = '''{"note_unid":"TEST006","note_items":[{"name":"sys_name","value":["Redis"]}]}'''
    result = parse_js_metadata_content(content, "test6.js")
    if test_result("missing status",
        {'note_unid': 'TEST006', 'sys_name': 'Redis', 'status': '', 'is_valid': False},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    if "Missing status" in result.parse_errors:
        print("  [PASS] Correct error: 'Missing status'")

    # =========================================================================
    # TEST: missing note_unid
    # =========================================================================
    print("\n[TEST] missing note_unid")
    total += 1
    content = '''{"note_items":[{"name":"sys_name","value":["MongoDB"]},{"name":"status","value":["New"]}]}'''
    result = parse_js_metadata_content(content, "test7.js")
    if test_result("missing note_unid",
        {'note_unid': '', 'sys_name': 'MongoDB', 'status': 'New', 'is_valid': False},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    if "Missing note_unid" in result.parse_errors:
        print("  [PASS] Correct error: 'Missing note_unid'")

    # =========================================================================
    # TEST: duplicate metadata fields (should use first found)
    # =========================================================================
    print("\n[TEST] duplicate metadata fields")
    total += 1
    content = '''{"note_unid":"TEST008","note_items":[{"name":"sys_name","value":["First"]},{"name":"sys_name","value":["Second"]},{"name":"status","value":["Open"]}]}'''
    result = parse_js_metadata_content(content, "test8.js")
    # Should return first occurrence
    if test_result("duplicate sys_name (first wins)",
        {'note_unid': 'TEST008', 'sys_name': 'First', 'status': 'Open', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: additional unknown metadata fields
    # =========================================================================
    print("\n[TEST] additional unknown metadata fields")
    total += 1
    content = '''{"note_unid":"TEST009","created":"2024-01-01","modified":"2024-01-02","author":"John","note_items":[{"name":"cc_sites","value":["NYC"]},{"name":"sys_name","value":["SystemA"]},{"name":"workflow","value":["Stage1"]},{"name":"status","value":["In Progress"]},{"name":"racks","value":["R1"]}]}'''
    result = parse_js_metadata_content(content, "test9.js")
    if test_result("ignores unknown fields",
        {'note_unid': 'TEST009', 'sys_name': 'SystemA', 'status': 'In Progress', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: hundreds of fields before and after
    # =========================================================================
    print("\n[TEST] hundreds of metadata fields before and after")
    total += 1
    # Generate content with 100 fields before and after
    fields_before = ",".join([f'{{"name":"field{i}","value":["val{i}"]}}' for i in range(100)])
    fields_after = ",".join([f'{{"name":"after{i}","value":["aval{i}"]}}' for i in range(100)])
    content = f'{{"note_unid":"TEST010","note_items":[{fields_before},{{"name":"sys_name","value":["DeepSearch"]}},{fields_after},{{"name":"status","value":["Found"]}}]}}'
    result = parse_js_metadata_content(content, "test10.js")
    if test_result("100 fields before/after target",
        {'note_unid': 'TEST010', 'sys_name': 'DeepSearch', 'status': 'Found', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: whitespace chaos
    # =========================================================================
    print("\n[TEST] whitespace chaos (tabs, newlines, spaces)")
    total += 1
    content = '''
    var  metadata  =
    {
        "note_unid"   :   "WHITESPACE_TEST"   ,

        "note_items"  :  [
            {
                "name"
                :
                "sys_name"
                ,
                "value"
                :
                [
                    "SpaceySystem"
                ]
            }
            ,
            {
                "name" : "status" ,
                "value" : [ "Spaced" ]
            }
        ]
    } ;
    '''
    result = parse_js_metadata_content(content, "test11.js")
    if test_result("handles whitespace chaos",
        {'note_unid': 'WHITESPACE_TEST', 'sys_name': 'SpaceySystem', 'status': 'Spaced', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: single quotes
    # =========================================================================
    print("\n[TEST] single quotes format")
    total += 1
    content = """{'note_unid':'SINGLE_Q','note_items':[{'name':'sys_name','value':['SingleQuoteSystem']},{'name':'status','value':['SingleStatus']}]}"""
    result = parse_js_metadata_content(content, "test12.js")
    if test_result("handles single quotes",
        {'note_unid': 'SINGLE_Q', 'sys_name': 'SingleQuoteSystem', 'status': 'SingleStatus', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: JavaScript variable declaration
    # =========================================================================
    print("\n[TEST] JavaScript variable declaration")
    total += 1
    content = '''var metadata = {"note_unid":"VAR_TEST","note_items":[{"name":"sys_name","value":["VarSystem"]},{"name":"status","value":["VarStatus"]}]}'''
    result = parse_js_metadata_content(content, "test13.js")
    if test_result("handles var declaration",
        {'note_unid': 'VAR_TEST', 'sys_name': 'VarSystem', 'status': 'VarStatus', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: value with special characters
    # =========================================================================
    print("\n[TEST] values with special characters")
    total += 1
    content = '''{"note_unid":"SPECIAL_123","note_items":[{"name":"sys_name","value":["System-With-Dashes"]},{"name":"status","value":["In Progress"]}]}'''
    result = parse_js_metadata_content(content, "test14.js")
    if test_result("handles special chars",
        {'note_unid': 'SPECIAL_123', 'sys_name': 'System-With-Dashes', 'status': 'In Progress', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: nested objects in note_items (canonical format)
    # =========================================================================
    print("\n[TEST] nested objects with additional properties (canonical format)")
    total += 1
    content = '''{"note_unid":"NESTED_TEST","note_items":[{"name":"sys_name","type":1280,"size":5,"last_modified":"2018-09-21","value":["NestedSystem"]},{"name":"status","type":1024,"value":["Nested"]}]}'''
    result = parse_js_metadata_content(content, "test15.js")
    if test_result("handles nested properties",
        {'note_unid': 'NESTED_TEST', 'sys_name': 'NestedSystem', 'status': 'Nested', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: reverse order (value before name)
    # =========================================================================
    print("\n[TEST] reverse field order (value before name)")
    total += 1
    content = '''{"note_unid":"REVERSE_TEST","note_items":[{"value":["ReverseSystem"],"name":"sys_name"},{"value":["ReverseStatus"],"name":"status"}]}'''
    result = parse_js_metadata_content(content, "test16.js")
    if test_result("handles reverse field order",
        {'note_unid': 'REVERSE_TEST', 'sys_name': 'ReverseSystem', 'status': 'ReverseStatus', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: escaped quotes in values
    # =========================================================================
    print("\n[TEST] escaped quotes in values")
    total += 1
    content = r'''{"note_unid":"ESCAPE_TEST","note_items":[{"name":"sys_name","value":["Sys \"Quoted\" Name"]},{"name":"status","value":["OK"]}]}'''
    result = parse_js_metadata_content(content, "test17.js")
    if test_result("handles escaped quotes",
        {'note_unid': 'ESCAPE_TEST', 'sys_name': 'Sys "Quoted" Name', 'status': 'OK', 'is_valid': True},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    # =========================================================================
    # TEST: extensibility - extracting additional fields
    # =========================================================================
    print("\n[TEST] extensibility - extract additional fields")
    total += 1
    content = '''{"note_unid":"EXT_TEST","note_items":[{"name":"cc_sites","value":["NYC"]},{"name":"sys_name","value":["ExtSystem"]},{"name":"workflow","value":["Stage1"]},{"name":"status","value":["Active"]},{"name":"racks","value":["Rack-A"]}]}'''
    fields = extract_multiple_fields(content, ['note_unid', 'sys_name', 'status', 'cc_sites', 'workflow', 'racks', 'unknown_field'])

    ext_passed = True
    if fields.get('note_unid') != 'EXT_TEST':
        print(f"  [FAIL] note_unid: expected 'EXT_TEST', got '{fields.get('note_unid')}'")
        ext_passed = False
    if fields.get('sys_name') != 'ExtSystem':
        print(f"  [FAIL] sys_name: expected 'ExtSystem', got '{fields.get('sys_name')}'")
        ext_passed = False
    if fields.get('status') != 'Active':
        print(f"  [FAIL] status: expected 'Active', got '{fields.get('status')}'")
        ext_passed = False
    if fields.get('cc_sites') != 'NYC':
        print(f"  [FAIL] cc_sites: expected 'NYC', got '{fields.get('cc_sites')}'")
        ext_passed = False
    if fields.get('workflow') != 'Stage1':
        print(f"  [FAIL] workflow: expected 'Stage1', got '{fields.get('workflow')}'")
        ext_passed = False
    if fields.get('racks') != 'Rack-A':
        print(f"  [FAIL] racks: expected 'Rack-A', got '{fields.get('racks')}'")
        ext_passed = False
    if fields.get('unknown_field') is not None:
        print(f"  [FAIL] unknown_field: expected None, got '{fields.get('unknown_field')}'")
        ext_passed = False

    if ext_passed:
        print("  [PASS] All additional fields extracted correctly")
        passed += 1

    # =========================================================================
    # TEST: all missing fields
    # =========================================================================
    print("\n[TEST] all fields missing")
    total += 1
    content = '''{}'''
    result = parse_js_metadata_content(content, "test_empty.js")
    if test_result("empty object",
        {'note_unid': '', 'sys_name': '', 'status': '', 'is_valid': False},
        {'note_unid': result.note_unid, 'sys_name': result.sys_name, 'status': result.status, 'is_valid': result.is_valid}):
        passed += 1

    if len(result.parse_errors) == 3:
        print("  [PASS] All 3 missing field errors reported")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
