#!/usr/bin/env python3
"""
Extract Classified Information Overlay 2022 controls from Section 6.

This script extracts control specifications from the 2022 version of the
Classified Information Overlay PDF, which has a simpler format than the
previous version.

Usage:
    python extract_classified_information.py <pdf_file>
"""

import fitz  # PyMuPDF
import json
import re
import sys
from typing import Dict, Optional, Tuple

def parse_control_header(text: str) -> Optional[Tuple[str, str]]:
    """
    Parse a control header line to extract control ID and name.
    
    Examples:
    - "AC-3(4), Access Enforcement | Discretionary Access Controls"
    - "AC-5, Separation of Duties"
    - "AC-1, (Access Control) Policy and Procedures"
    
    Returns: (control_id, control_name) or None
    """
    # Pattern for base controls and enhancements
    pattern = r'^([A-Z]{2}-\d{1,2}(?:\(\d+\))?),\s*(.+)$'
    match = re.match(pattern, text.strip())
    if match:
        control_id = match.group(1)
        control_name = match.group(2).strip()
        
        # Remove family name in parentheses at the beginning if present
        # e.g., "(Access Control) Policy and Procedures" -> "Policy and Procedures"
        family_pattern = r'^\([^)]+\)\s*(.+)$'
        family_match = re.match(family_pattern, control_name)
        if family_match:
            control_name = family_match.group(1)
            
        return control_id, control_name
    return None

def extract_controls_from_pdf(pdf_path: str) -> Dict:
    """
    Extract all controls from Section 6 of the PDF.
    
    Returns a dictionary mapping control IDs to their specifications.
    """
    doc = fitz.open(pdf_path)
    controls = {}
    
    # Find the start of Section 6
    section_6_start = None
    section_7_start = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        if "6.  Detailed Overlay Control Specifications" in text or "6. Detailed Overlay Control Specifications" in text:
            section_6_start = page_num
            print(f"Found Section 6 on page {page_num + 1}")
        elif section_6_start is not None and ("7." in text and "Implementation Considerations" in text):
            section_7_start = page_num
            print(f"Found Section 7 on page {page_num + 1}")
            break
    
    if section_6_start is None:
        print("ERROR: Could not find Section 6")
        return controls
    
    # Process pages in Section 6
    # Include the page where section 7 starts since it may have controls before section 7
    end_page = (section_7_start + 1) if section_7_start else len(doc)
    
    current_control = None
    current_field = None
    
    for page_num in range(section_6_start, end_page):
        page = doc[page_num]
        text = page.get_text()
        
        # Split into lines and process
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Stop if we hit Section 7
            if "7." in line and "Implementation Considerations" in line:
                print(f"Stopping at Section 7 on page {page_num + 1}")
                doc.close()
                return controls
            
            # Skip empty lines and page headers/footers
            if not line or line == "Classified System Overlay" or line.isdigit():
                continue
            if "Attachment 5 to Appendix E" in line:
                continue
            if line == "09/30/2022":
                continue
                
            # Check if this is a control header
            control_info = parse_control_header(line)
            if control_info:
                control_id, control_name = control_info
                current_control = control_id
                current_field = None
                
                controls[control_id] = {
                    "control_id": control_id,
                    "name": control_name,
                    "selected": True,  # All controls in this overlay are selected
                    "justification": None,
                    "parameter_value": None,
                    "guidance": None,
                    "references": None
                }
                continue
            
            # Check for field headers
            if current_control:
                if line.startswith("Justification to Select:"):
                    current_field = "justification"
                    content = line[len("Justification to Select:"):].strip()
                    if content:
                        controls[current_control]["justification"] = content
                elif line.startswith("Parameter Value:"):
                    current_field = "parameter_value"
                    content = line[len("Parameter Value:"):].strip()
                    if content:
                        controls[current_control]["parameter_value"] = content
                elif line.startswith("Guidance:"):
                    current_field = "guidance"
                    content = line[len("Guidance:"):].strip()
                    if content:
                        controls[current_control]["guidance"] = content
                elif line.startswith("Reference(s):") or line.startswith("Reference:"):
                    current_field = "references"
                    content = line[line.find(":") + 1:].strip()
                    if content:
                        controls[current_control]["references"] = content
                # Continue previous field
                elif current_field and line:
                    # Check if this might be a new control (safety check)
                    if not parse_control_header(line):
                        if controls[current_control][current_field]:
                            controls[current_control][current_field] += " " + line
                        else:
                            controls[current_control][current_field] = line
    
    doc.close()
    return controls

def print_summary(controls: Dict):
    """Print a summary of extracted controls."""
    print(f"\n=== EXTRACTION SUMMARY ===")
    print(f"Total controls extracted: {len(controls)}")
    
    if not controls:
        print("No controls found!")
        return
    
    # Count by family
    families = {}
    base_controls = 0
    enhancements = 0
    
    for control_id in controls.keys():
        family = control_id.split('-')[0]
        families[family] = families.get(family, 0) + 1
        
        if '(' in control_id:
            enhancements += 1
        else:
            base_controls += 1
    
    print(f"Base controls: {base_controls}")
    print(f"Enhancements: {enhancements}")
    
    print("\nControls by family:")
    for family, count in sorted(families.items()):
        print(f"  {family}: {count}")
    
    # Show some examples
    print("\nFirst 5 controls:")
    for i, (control_id, control) in enumerate(list(controls.items())[:5]):
        print(f"\n{control_id}: {control['name']}")
        if control['justification']:
            print(f"  Justification: {control['justification'][:100]}...")
        if control['parameter_value']:
            print(f"  Parameter: {control['parameter_value'][:100]}...")
        if control['guidance']:
            print(f"  Guidance: {control['guidance'][:100]}...")
        if control['references']:
            print(f"  References: {control['references']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_classified_information.py <pdf_file>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    output_file = "extracted_classified_information.json"
    
    print("Extracting Classified Information Overlay...")
    controls = extract_controls_from_pdf(pdf_file)
    
    if controls:
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(controls, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(controls)} controls to {output_file}")
        
        print_summary(controls)
    else:
        print("No controls were extracted.")

if __name__ == "__main__":
    main()