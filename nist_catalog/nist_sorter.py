#!/usr/bin/env python3
"""
NIST SP 800-53 Control Catalog JSON Sorter

This script sorts the NIST SP 800-53 control catalog JSON file so that:
1. Controls are grouped by family
2. Within each family, controls are sorted in ascending order
3. Control enhancements always appear after their parent control
4. Enhancement numbers are sorted numerically (e.g., AC-1(1), AC-1(2), AC-1(10))

Usage:
    python nist_sorter.py input_file.json [output_file.json]

If no output file is specified, the script will overwrite the input file.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple


def parse_control_id(control_id: str) -> Tuple[str, int, int]:
    """
    Parse a control ID and return components for sorting.
    
    Args:
        control_id: Control ID like "AC-1", "AC-1(1)", "AC-14(1)", etc.
        
    Returns:
        Tuple of (family, base_number, enhancement_number)
        Enhancement number is 0 for base controls, positive for enhancements
    """
    # Match patterns like "AC-1" or "AC-1(1)"
    match = re.match(r'^([A-Z]{2,3})-(\d+)(?:\((\d+)\))?$', control_id)
    
    if not match:
        raise ValueError(f"Invalid control ID format: {control_id}")
    
    family = match.group(1)
    base_number = int(match.group(2))
    enhancement_number = int(match.group(3)) if match.group(3) else 0
    
    return family, base_number, enhancement_number


def sort_controls(controls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort controls by family, then by base control number, then by enhancement number.
    
    Args:
        controls: List of control dictionaries
        
    Returns:
        Sorted list of controls
    """
    def sort_key(control: Dict[str, Any]) -> Tuple[str, int, int]:
        """Generate sort key for a control."""
        control_id = control.get('id', '')
        try:
            return parse_control_id(control_id)
        except ValueError as e:
            print(f"Warning: {e}", file=sys.stderr)
            # Fallback: put malformed IDs at the end
            return ('ZZZ', 9999, 9999)
    
    return sorted(controls, key=sort_key)


def validate_json_structure(data: Dict[str, Any]) -> None:
    """
    Validate that the JSON has the expected structure.
    
    Args:
        data: Parsed JSON data
        
    Raises:
        ValueError: If structure is not as expected
    """
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    
    if 'controls' not in data:
        raise ValueError("JSON must contain a 'controls' key")
    
    if not isinstance(data['controls'], list):
        raise ValueError("'controls' must be an array")
    
    # Check a few sample controls for expected structure
    controls = data['controls']
    if controls:
        sample_control = controls[0]
        required_fields = ['id', 'family']
        for field in required_fields:
            if field not in sample_control:
                print(f"Warning: Control missing expected field '{field}'", file=sys.stderr)


def print_sorting_summary(original_controls: List[Dict[str, Any]], 
                         sorted_controls: List[Dict[str, Any]]) -> None:
    """Print a summary of the sorting operation."""
    
    # Count controls by family
    def count_by_family(controls):
        family_counts = {}
        for control in controls:
            family = control.get('family', 'Unknown')
            if family not in family_counts:
                family_counts[family] = {'base': 0, 'enhancements': 0}
            
            if control.get('isEnhancement', False):
                family_counts[family]['enhancements'] += 1
            else:
                family_counts[family]['base'] += 1
        return family_counts
    
    original_counts = count_by_family(original_controls)
    sorted_counts = count_by_family(sorted_controls)
    
    print(f"Processed {len(sorted_controls)} controls across {len(sorted_counts)} families:")
    
    for family in sorted(sorted_counts.keys()):
        base_count = sorted_counts[family]['base']
        enh_count = sorted_counts[family]['enhancements']
        total = base_count + enh_count
        print(f"  {family}: {total} total ({base_count} base, {enh_count} enhancements)")
    
    # Check if any controls were moved
    moves = 0
    for i, (orig, sort) in enumerate(zip(original_controls, sorted_controls)):
        if orig['id'] != sort['id']:
            moves += 1
    
    if moves > 0:
        print(f"\nReordered {moves} controls for proper sorting.")
    else:
        print("\nAll controls were already in correct order.")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python nist_sorter.py input_file.json [output_file.json]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file
    
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    try:
        # Read and parse JSON
        print(f"Reading {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate structure
        validate_json_structure(data)
        
        # Get controls array
        original_controls = data['controls']
        print(f"Found {len(original_controls)} controls to sort.")
        
        # Sort controls
        print("Sorting controls...")
        sorted_controls = sort_controls(original_controls)
        
        # Update data with sorted controls
        data['controls'] = sorted_controls
        
        # Write output
        print(f"Writing sorted controls to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print_sorting_summary(original_controls, sorted_controls)
        print(f"\nSorting complete! Output saved to: {output_file}")
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
