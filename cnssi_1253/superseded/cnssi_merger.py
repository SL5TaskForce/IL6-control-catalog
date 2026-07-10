#!/usr/bin/env python3
"""
Script to merge extracted_cnssi_1253_selections.json with extracted_cnssi_1253_overlay.json

Merges the two JSON files according to the following rules:
1. If a control exists in both files, do nothing (keep overlay version)
2. If a control exists in overlay but not in selections, log debug message but do nothing
3. If a control exists in selections but not in overlay, add it to overlay in the proper format
"""

import json
import logging
import re
from typing import Dict, Any, Set

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load JSON file and return its contents."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded {filepath}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        raise

def extract_control_ids_from_selections(selections_data: list) -> Set[str]:
    """Extract control IDs from the selections JSON (which is a list format)."""
    control_ids = set()
    for control in selections_data:
        if isinstance(control, dict) and 'id' in control:
            control_ids.add(control['id'])
    return control_ids

def extract_control_ids_from_overlay(overlay_data: dict) -> Set[str]:
    """Extract control IDs from the overlay JSON (which is a dict format)."""
    return set(overlay_data.keys())

def convert_selection_to_overlay_format(selection_control: dict) -> dict:
    """
    Convert a control from selections format to overlay format.
    
    Selections format: {"id": "AC-1", "name": "Access Control Policy and Procedures"}
    Overlay format: {
        "control_text": "",
        "defined_value": "",
        "selected": true
    }
    """
    overlay_control = {
        "control_text": "",
        "defined_value": "",
        "selected": True
    }
    return overlay_control

def natural_sort_key(control_id: str) -> tuple:
    """
    Create a sort key for natural sorting of control IDs.
    This handles proper ordering like AC-1, AC-2, ..., AC-10, AC-11, etc.
    and AC-1(1), AC-1(2), ..., AC-1(10), AC-1(11), etc.
    """
    # Split the control ID into parts
    match = re.match(r'^([A-Z]{2})-(\d+)(?:\((\d+)\))?$', control_id)
    if match:
        family = match.group(1)
        base_num = int(match.group(2))
        enhancement_num = int(match.group(3)) if match.group(3) else 0
        return (family, base_num, enhancement_num)
    else:
        # Fallback for any malformed IDs
        return (control_id, 0, 0)

def merge_json_files(selections_file: str, overlay_file: str, output_file: str):
    """
    Merge the selections and overlay JSON files according to the specified rules.
    Maintains proper alphabetical and numerical ordering of controls.
    """
    logger.info("Starting merge process...")
    
    # Load both JSON files
    selections_data = load_json_file(selections_file)
    overlay_data = load_json_file(overlay_file)
    
    # Extract control IDs from both files
    selections_control_ids = extract_control_ids_from_selections(selections_data)
    overlay_control_ids = extract_control_ids_from_overlay(overlay_data)
    
    logger.info(f"Found {len(selections_control_ids)} controls in selections file")
    logger.info(f"Found {len(overlay_control_ids)} controls in overlay file")
    
    # Rule 1: Controls that exist in both files - do nothing (keep overlay version) but add selected field
    common_controls = selections_control_ids.intersection(overlay_control_ids)
    logger.info(f"Found {len(common_controls)} controls that exist in both files - keeping overlay versions and marking as selected")
    
    # Add selected field to common controls
    for control_id in common_controls:
        overlay_data[control_id]["selected"] = True
    
    # Rule 2: Controls that exist in overlay but not in selections - log debug message and mark as not selected
    overlay_only_controls = overlay_control_ids - selections_control_ids
    for control_id in sorted(overlay_only_controls, key=natural_sort_key):
        logger.debug(f"Control {control_id} exists in overlay but not in selections file")
        overlay_data[control_id]["selected"] = False
    logger.info(f"Found {len(overlay_only_controls)} controls that exist only in overlay file - marked as not selected")
    
    # Rule 3: Controls that exist in selections but not in overlay - add to overlay with selected=true
    selections_only_controls = selections_control_ids - overlay_control_ids
    logger.info(f"Found {len(selections_only_controls)} controls that exist only in selections file - adding to overlay and marking as selected")
    
    # Create a lookup dictionary for selections controls
    selections_lookup = {}
    for control in selections_data:
        if isinstance(control, dict) and 'id' in control:
            selections_lookup[control['id']] = control
    
    # Add missing controls to overlay data (but don't save yet)
    added_count = 0
    for control_id in selections_only_controls:
        if control_id in selections_lookup:
            selection_control = selections_lookup[control_id]
            overlay_format_control = convert_selection_to_overlay_format(selection_control)
            overlay_data[control_id] = overlay_format_control
            added_count += 1
            logger.debug(f"Added control {control_id} to overlay format with selected=true")
    
    logger.info(f"Successfully added {added_count} controls from selections to overlay")
    
    # Create ordered dictionary for final output
    # Sort all control IDs using natural sorting
    all_control_ids = list(overlay_data.keys())
    sorted_control_ids = sorted(all_control_ids, key=natural_sort_key)
    
    # Build the final ordered dictionary
    ordered_merged_data = {}
    for control_id in sorted_control_ids:
        ordered_merged_data[control_id] = overlay_data[control_id]
    
    # Save the merged data with proper ordering
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ordered_merged_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved merged data to {output_file}")
    except Exception as e:
        logger.error(f"Error saving merged data: {e}")
        raise
    
    # Print summary
    print("\n" + "="*60)
    print("MERGE SUMMARY")
    print("="*60)
    print(f"Controls in selections file: {len(selections_control_ids)}")
    print(f"Controls in overlay file: {len(overlay_control_ids)}")
    print(f"Controls existing in both files: {len(common_controls)}")
    print(f"Controls only in overlay file: {len(overlay_only_controls)}")
    print(f"Controls only in selections file: {len(selections_only_controls)}")
    print(f"Controls added to merged file: {added_count}")
    print(f"Total controls in merged file: {len(ordered_merged_data)}")
    print(f"Output saved to: {output_file}")
    print("="*60)

def main():
    """Main function to run the merge process."""
    selections_file = "extracted_cnssi_1253_selections.json"
    overlay_file = "extracted_cnssi_1253_overlay.json"
    output_file = "merged_cnssi_1253.json"
    
    try:
        merge_json_files(selections_file, overlay_file, output_file)
    except Exception as e:
        logger.error(f"Merge process failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())