#!/usr/bin/env python3
"""
Generate a simple summary of CNSSI 1253 version changes for reporting.
"""

import json

def main():
    # Load data
    with open('merged_cnssi_1253.json', 'r') as f:
        old_data = json.load(f)
    
    with open('extracted_cnssi_1253_2022.json', 'r') as f:
        new_data = json.load(f)
    
    # Get selected controls
    old_selected = set()
    for control_id, control in old_data.items():
        if control.get('selected', False):
            old_selected.add(control_id)
    
    new_selected = set()
    for control_id, control in new_data.items():
        if control.get('selected', False) and not control.get('withdrawn', False):
            # Check if any CIA selections exist
            if 'selections' in control:
                for cia in ['confidentiality', 'integrity', 'availability']:
                    if any(control['selections'].get(cia, {}).get(level, False) 
                           for level in ['low', 'moderate', 'high']):
                        new_selected.add(control_id)
                        break
    
    # Calculate differences
    deselected = sorted(old_selected - new_selected)
    newly_selected = sorted(new_selected - old_selected)
    
    # Write summary
    with open('CNSSI_1253_version_change_summary.txt', 'w') as f:
        f.write("CNSSI 1253 VERSION CHANGE SUMMARY\n")
        f.write("=================================\n\n")
        
        f.write("STATISTICS:\n")
        f.write(f"- Old version (based on NIST 800-53 Rev 4): {len(old_selected)} selected controls\n")
        f.write(f"- New version (based on NIST 800-53 Rev 5): {len(new_selected)} selected controls\n")
        f.write(f"- Controls deselected: {len(deselected)}\n")
        f.write(f"- Controls newly selected: {len(newly_selected)}\n")
        f.write(f"- Net change: {len(new_selected) - len(old_selected):+d} controls\n")
        
        f.write("\n\nCONTROLS DESELECTED IN NEW VERSION:\n")
        f.write("------------------------------------\n")
        for control_id in deselected:
            # Check if withdrawn
            if control_id in new_data and new_data[control_id].get('withdrawn', False):
                f.write(f"{control_id} (withdrawn in Rev 5)\n")
            else:
                f.write(f"{control_id}\n")
        
        f.write("\n\nCONTROLS NEWLY SELECTED IN NEW VERSION:\n")
        f.write("----------------------------------------\n")
        for control_id in newly_selected:
            f.write(f"{control_id}\n")
    
    print("Summary written to: CNSSI_1253_version_change_summary.txt")

if __name__ == "__main__":
    main()