#!/usr/bin/env python3
"""
Compare CNSSI 1253 old version (Rev 4 based) with new version (Rev 5 based).
Shows differences in control selections between the two versions.
"""

import json
from collections import defaultdict

def load_old_cnssi():
    """Load the old CNSSI 1253 format (merged from selection and overlay files)."""
    with open('merged_cnssi_1253.json', 'r') as f:
        return json.load(f)

def load_new_cnssi():
    """Load the new CNSSI 1253 2022 format."""
    with open('extracted_cnssi_1253_2022.json', 'r') as f:
        return json.load(f)

def get_old_selected_controls(old_data):
    """Get set of selected controls from old format."""
    selected = set()
    for control_id, control_data in old_data.items():
        if control_data.get('selected', False):
            selected.add(control_id)
    return selected

def get_new_selected_controls(new_data):
    """Get set of selected controls from new format."""
    selected = set()
    for control_id, control_data in new_data.items():
        if control_data.get('selected', False) and not control_data.get('withdrawn', False):
            # Check if any CIA selections exist
            if 'selections' in control_data:
                has_selection = False
                for cia in ['confidentiality', 'integrity', 'availability']:
                    if control_data['selections'].get(cia, {}):
                        for level in ['low', 'moderate', 'high']:
                            if control_data['selections'][cia].get(level, False):
                                has_selection = True
                                break
                        if has_selection:
                            break
                if has_selection:
                    selected.add(control_id)
            elif control_data.get('selected', False):
                selected.add(control_id)
    return selected

def compare_cia_selections(new_data):
    """Analyze CIA selections in the new format."""
    cia_stats = {
        'confidentiality': defaultdict(int),
        'integrity': defaultdict(int),
        'availability': defaultdict(int)
    }
    
    for control_id, control_data in new_data.items():
        if control_data.get('selected', False) and not control_data.get('withdrawn', False):
            if 'selections' in control_data:
                for cia in ['confidentiality', 'integrity', 'availability']:
                    for level in ['low', 'moderate', 'high']:
                        if control_data['selections'].get(cia, {}).get(level, False):
                            cia_stats[cia][level] += 1
    
    return cia_stats

def main():
    print("=== CNSSI 1253 Version Comparison ===\n")
    
    # Load data
    old_data = load_old_cnssi()
    new_data = load_new_cnssi()
    
    print(f"Old version (Rev 4 based): {len(old_data)} total controls")
    print(f"New version (Rev 5 based): {len(new_data)} total controls")
    
    # Get selected controls
    old_selected = get_old_selected_controls(old_data)
    new_selected = get_new_selected_controls(new_data)
    
    print(f"\nOld version selected controls: {len(old_selected)}")
    print(f"New version selected controls: {len(new_selected)}")
    
    # Find differences
    only_old = old_selected - new_selected
    only_new = new_selected - old_selected
    both = old_selected & new_selected
    
    print(f"\n=== Selection Differences ===")
    print(f"Controls in both versions: {len(both)}")
    print(f"Controls only in old version: {len(only_old)}")
    print(f"Controls only in new version: {len(only_new)}")
    
    if only_old:
        print("\n--- Controls Selected Only in Old Version ---")
        for control_id in sorted(only_old):
            old_control = old_data.get(control_id, {})
            new_control = new_data.get(control_id, {})
            print(f"{control_id}: {old_control.get('control_text', 'N/A')[:60]}...")
            if control_id in new_data:
                if new_control.get('withdrawn', False):
                    print(f"  → Withdrawn in new version")
                else:
                    print(f"  → Not selected in new version")
            else:
                print(f"  → Not present in new version")
    
    if only_new:
        print("\n--- Controls Selected Only in New Version ---")
        for control_id in sorted(only_new)[:20]:  # Show first 20
            new_control = new_data.get(control_id, {})
            print(f"{control_id}: {new_control.get('title', 'N/A')}")
            if new_control.get('justification'):
                print(f"  Justification: {new_control['justification'][:80]}...")
    
    # Analyze CIA selections in new format
    print("\n=== CIA Triad Analysis (New Version) ===")
    cia_stats = compare_cia_selections(new_data)
    
    for cia in ['confidentiality', 'integrity', 'availability']:
        print(f"\n{cia.capitalize()}:")
        for level in ['low', 'moderate', 'high']:
            count = cia_stats[cia][level]
            print(f"  {level.capitalize()}: {count} controls")
    
    # Check for controls with parameter values
    print("\n=== Parameter Values ===")
    old_with_params = sum(1 for c in old_data.values() if c.get('defined_value'))
    new_with_params = sum(1 for c in new_data.values() if c.get('parameter_value'))
    print(f"Old version controls with defined values: {old_with_params}")
    print(f"New version controls with parameter values: {new_with_params}")
    
    # Sample some parameter value differences
    print("\n--- Sample Parameter Values (New Version) ---")
    count = 0
    for control_id, control in new_data.items():
        if control.get('parameter_value') and count < 5:
            print(f"{control_id}: {control['parameter_value'][:80]}...")
            count += 1

if __name__ == "__main__":
    main()