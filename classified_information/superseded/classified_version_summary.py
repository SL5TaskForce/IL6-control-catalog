#!/usr/bin/env python3
"""
Generate a simple summary of Classified Information Overlay version changes for reporting.
"""

import json

def main():
    # Load data
    with open('extracted_classified_information_overlay.json', 'r') as f:
        old_data = json.load(f)
    
    with open('extracted_classified_information_2022.json', 'r') as f:
        new_data = json.load(f)
    
    # Get control sets
    old_controls = set(old_data.keys())
    new_controls = set(new_data.keys())
    
    # Calculate differences
    removed = sorted(old_controls - new_controls)
    added = sorted(new_controls - old_controls)
    
    # Write summary
    with open('Classified_Information_version_change_summary.txt', 'w') as f:
        f.write("CLASSIFIED INFORMATION OVERLAY VERSION CHANGE SUMMARY\n")
        f.write("====================================================\n\n")
        
        f.write("STATISTICS:\n")
        f.write(f"- Old version (based on NIST 800-53 Rev 4): {len(old_controls)} controls\n")
        f.write(f"- New version (based on NIST 800-53 Rev 5): {len(new_controls)} controls\n")
        f.write(f"- Controls removed: {len(removed)}\n")
        f.write(f"- Controls added: {len(added)}\n")
        f.write(f"- Net change: {len(new_controls) - len(old_controls):+d} controls\n")
        
        f.write("\n\nCONTROLS REMOVED IN NEW VERSION:\n")
        f.write("---------------------------------\n")
        for control_id in removed:
            f.write(f"{control_id}\n")
        
        f.write("\n\nCONTROLS ADDED IN NEW VERSION:\n")
        f.write("-------------------------------\n")
        for control_id in added:
            f.write(f"{control_id}\n")
    
    print("Summary written to: Classified_Information_version_change_summary.txt")

if __name__ == "__main__":
    main()