#!/usr/bin/env python3
"""
Compare Classified Information Overlay old version (Rev 4 based) with new version (Rev 5 based).
Shows differences in control selections between the two versions.
"""

import json
from collections import defaultdict

def load_old_classified():
    """Load the old Classified Information Overlay format."""
    with open('extracted_classified_information_overlay.json', 'r') as f:
        return json.load(f)

def load_new_classified():
    """Load the new Classified Information 2022 format."""
    with open('extracted_classified_information_2022.json', 'r') as f:
        return json.load(f)

def analyze_attributes(old_data, new_data):
    """Analyze differences in control attributes between versions."""
    # Count attribute types in old format
    old_attrs = defaultdict(int)
    for control in old_data.values():
        for attr in control.get('attributes', {}):
            old_attrs[attr] += 1
    
    # Count field types in new format
    new_fields = defaultdict(int)
    for control in new_data.values():
        if control.get('justification'):
            new_fields['justification'] += 1
        if control.get('parameter_value'):
            new_fields['parameter_value'] += 1
        if control.get('guidance'):
            new_fields['guidance'] += 1
        if control.get('references'):
            new_fields['references'] += 1
    
    return old_attrs, new_fields

def main():
    print("=== Classified Information Overlay Version Comparison ===\n")
    
    # Load data
    old_data = load_old_classified()
    new_data = load_new_classified()
    
    print(f"Old version (Rev 4 based): {len(old_data)} controls")
    print(f"New version (Rev 5 based): {len(new_data)} controls")
    
    # Get control sets
    old_controls = set(old_data.keys())
    new_controls = set(new_data.keys())
    
    # Find differences
    only_old = old_controls - new_controls
    only_new = new_controls - old_controls
    both = old_controls & new_controls
    
    print(f"\n=== Control Coverage ===")
    print(f"Controls in both versions: {len(both)}")
    print(f"Controls only in old version: {len(only_old)}")
    print(f"Controls only in new version: {len(only_new)}")
    
    if only_old:
        print("\n--- Controls Only in Old Version ---")
        for control_id in sorted(only_old):
            old_control = old_data[control_id]
            print(f"{control_id}: {old_control.get('name', 'N/A')}")
            # Check if control might have different ID format in new version
            base_id = control_id.split('(')[0]
            similar = [cid for cid in new_controls if cid.startswith(base_id)]
            if similar:
                print(f"  → Possible matches in new version: {similar}")
    
    if only_new:
        print("\n--- Controls Only in New Version ---")
        for control_id in sorted(only_new):
            new_control = new_data[control_id]
            print(f"{control_id}: {new_control.get('name', 'N/A')}")
    
    # Analyze attributes
    print("\n=== Attribute/Field Analysis ===")
    old_attrs, new_fields = analyze_attributes(old_data, new_data)
    
    print("\nOld version attribute types:")
    for attr, count in sorted(old_attrs.items()):
        print(f"  {attr}: {count} controls")
    
    print("\nNew version field types:")
    for field, count in sorted(new_fields.items()):
        print(f"  {field}: {count} controls")
    
    # Show some examples of controls in both versions
    print("\n=== Sample Control Comparisons ===")
    sample_controls = sorted(both)[:5]
    
    for control_id in sample_controls:
        print(f"\n{control_id}:")
        old_control = old_data[control_id]
        new_control = new_data[control_id]
        
        print(f"  Old name: {old_control.get('name', 'N/A')}")
        print(f"  New name: {new_control.get('name', 'N/A')}")
        
        # Compare attributes
        old_attrs = old_control.get('attributes', {})
        if old_attrs:
            print("  Old attributes:")
            for attr, value in old_attrs.items():
                if value:
                    print(f"    {attr}: {str(value)[:60]}...")
        
        print("  New fields:")
        if new_control.get('justification'):
            print(f"    justification: {new_control['justification'][:60]}...")
        if new_control.get('parameter_value'):
            print(f"    parameter_value: {new_control['parameter_value'][:60]}...")
        if new_control.get('guidance'):
            print(f"    guidance: {new_control['guidance'][:60]}...")
        if new_control.get('references'):
            print(f"    references: {new_control['references'][:60]}...")
    
    # Count families
    print("\n=== Control Family Distribution ===")
    old_families = defaultdict(int)
    new_families = defaultdict(int)
    
    for control_id in old_controls:
        family = control_id.split('-')[0]
        old_families[family] += 1
    
    for control_id in new_controls:
        family = control_id.split('-')[0]
        new_families[family] += 1
    
    all_families = sorted(set(old_families.keys()) | set(new_families.keys()))
    
    print("\nFamily | Old | New | Diff")
    print("-------|-----|-----|-----")
    for family in all_families:
        old_count = old_families[family]
        new_count = new_families[family]
        diff = new_count - old_count
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        print(f"{family:6} | {old_count:3} | {new_count:3} | {diff_str:4}")
    
    print(f"\nTotal  | {len(old_controls):3} | {len(new_controls):3} | {len(new_controls) - len(old_controls):+4}")

if __name__ == "__main__":
    main()