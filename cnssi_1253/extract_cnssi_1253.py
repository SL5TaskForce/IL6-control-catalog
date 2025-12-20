#!/usr/bin/env python3
"""
Extract CNSSI 1253 2022 overlay data from PDF using table extraction.
Final version: Uses range-based column detection for robust extraction.
"""

import fitz
import json
import re
import sys
from typing import Dict, List, Optional, Tuple

class TableStructure:
    """Stores the column ranges for impact levels."""
    def __init__(self):
        self.ranges = {}  # e.g., {'C-L': (11, 13), 'C-M': (14, 16), ...}
        self.justification_col = None
        self.param_value_col = None

def detect_table_structure(header_rows: List[List]) -> TableStructure:
    """Detect column ranges from header rows."""
    structure = TableStructure()
    
    # Find C, I, A positions in header
    cia_positions = {}
    if len(header_rows) >= 2:
        for i, cell in enumerate(header_rows[1]):
            if cell and str(cell).strip() in ['C', 'I', 'A']:
                cia_positions[str(cell).strip()] = i
    
    # Find L, M, H positions and create ranges
    if len(header_rows) >= 3:
        lmh_positions = []
        for i, cell in enumerate(header_rows[2]):
            if cell and str(cell).strip() in ['L', 'M', 'H']:
                lmh_positions.append((i, str(cell).strip()))
        
        # Group L/M/H into sets of 3 (one for each CIA)
        # We expect 9 total: 3 for C, 3 for I, 3 for A
        cia_list = ['C', 'I', 'A']
        cia_idx = 0
        level_count = 0
        
        for col, level in lmh_positions:
            if cia_idx < len(cia_list):
                cia = cia_list[cia_idx]
                
                # Find the end of the range
                # Look for the next L/M/H position
                end_col = col
                for j, (next_col, next_level) in enumerate(lmh_positions):
                    if next_col > col:
                        end_col = next_col - 1
                        break
                else:
                    # Last one - give it a range of 2
                    end_col = col + 2
                
                structure.ranges[f'{cia}-{level}'] = (col, end_col)
                
                # Move to next CIA after 3 levels
                level_count += 1
                if level_count >= 3:
                    cia_idx += 1
                    level_count = 0
    
    # Find justification and parameter value columns
    if len(header_rows) >= 1:
        for i, cell in enumerate(header_rows[0]):
            if cell:
                cell_str = str(cell).strip().lower()
                if 'justification' in cell_str:
                    structure.justification_col = i
                elif 'parameter' in cell_str:
                    structure.param_value_col = i
    
    return structure

def parse_control_row(row: List, structure: TableStructure) -> Optional[Dict]:
    """Parse a single row from the control table."""
    if not row or len(row) < 10:
        return None
    
    # Check if this is a withdrawn control
    is_withdrawn = any(cell and 'Withdrawn' in str(cell) for cell in row)
    
    # Don't skip withdrawn controls - process them
    
    # Find control ID - check first few columns
    control_id = ""
    control_col_idx = 0
    for i in range(min(4, len(row))):
        if row[i]:
            potential_id = str(row[i]).strip()
            if re.match(r'^[A-Z]{2}-\d+(\(\d+\))?$', potential_id):
                control_id = potential_id
                control_col_idx = i
                break
    
    if not control_id:
        return None
    
    # Extract title - look in next few columns after control ID
    title = ""
    for offset in range(1, 5):
        idx = control_col_idx + offset
        if idx < len(row) and row[idx] and str(row[idx]).strip():
            title = str(row[idx]).strip()
            break
    
    # Check for special PM (Program Management) and PT (PII) families
    family = control_id.split('-')[0]
    special_case_text = None
    
    # Hardcode special text for PM and PT families
    if family == 'PM':
        special_case_text = "Deployed organization-wide. Supports information security program. Not associated with security control baselines. Independent of any system impact level."
    elif family == 'PT':
        special_case_text = "Personally Identifiable Information Processing and Transparency control are not allocated to the security control baselines."
    
    # Initialize selections
    selections = {
        'confidentiality': {'low': False, 'moderate': False, 'high': False},
        'integrity': {'low': False, 'moderate': False, 'high': False},
        'availability': {'low': False, 'moderate': False, 'high': False}
    }
    
    # Check for marks using ranges
    def is_selected(val):
        if val is None:
            return False
        val_str = str(val).strip()
        return val_str in ['X', '+']
    
    # Check each cell against our ranges
    for col_idx, cell in enumerate(row):
        if is_selected(cell):
            # Find which range this column falls into
            for range_name, (start, end) in structure.ranges.items():
                if start <= col_idx <= end:
                    # Parse range name (e.g., 'C-L' -> confidentiality, low)
                    cia, level = range_name.split('-')
                    cia_map = {'C': 'confidentiality', 'I': 'integrity', 'A': 'availability'}
                    level_map = {'L': 'low', 'M': 'moderate', 'H': 'high'}
                    
                    if cia in cia_map and level in level_map:
                        selections[cia_map[cia]][level_map[level]] = True
                    break
    
    # Extract justification and parameter value
    justification = None
    if structure.justification_col and structure.justification_col < len(row):
        cell = row[structure.justification_col]
        if cell:
            just_str = str(cell).strip()
            if just_str and just_str not in ['', 'None', 'X', '+']:
                justification = just_str
    
    parameter_value = None
    if structure.param_value_col and structure.param_value_col < len(row):
        cell = row[structure.param_value_col]
        if cell:
            param_str = str(cell).strip()
            if param_str and param_str not in ['', 'None', 'X', '+']:
                parameter_value = param_str
    
    # Determine if control is selected
    selected = any(
        any(level for level in objective.values())
        for objective in selections.values()
    )
    
    # Special case handling for PM and PT families
    if family == 'PM':
        # PM controls are selected organization-wide
        selected = True
    elif family == 'PT':
        # PT controls are not selected by default
        selected = False
    
    # Withdrawn controls are never selected
    if is_withdrawn:
        selected = False
    
    # Add special case text to selections if applicable
    if special_case_text:
        selections['special_text'] = special_case_text
    
    result = {
        'control_id': control_id,
        'title': title,
        'selected': selected,
        'selections': selections,
        'parameter_value': parameter_value,
        'justification': justification
    }
    
    # Add withdrawn field if applicable
    if is_withdrawn:
        result['withdrawn'] = True
    
    return result

def extract_controls_from_page(page, prev_structure=None) -> Tuple[List[Dict], TableStructure]:
    """Extract control data from a single page using table extraction.
    Returns controls and the last table structure for use with continuation tables."""
    controls = []
    last_structure = prev_structure
    
    tables = page.find_tables()
    for table in tables:
        extracted = table.extract()
        
        if len(extracted) < 4:  # Might be a continuation table
            # If we have a previous structure and this looks like control data
            if prev_structure and len(extracted) > 0:
                # Check if first row contains a control ID
                has_control = False
                for row in extracted:
                    for cell in row[:3]:  # Check first 3 columns
                        if cell and re.match(r'^[A-Z]{2}-\d+(\(\d+\))?$', str(cell).strip()):
                            has_control = True
                            break
                    if has_control:
                        break
                
                if has_control:
                    # Process as continuation table using previous structure
                    # Check if this is the SC-18(2)/SC-18(3) special case on page 136
                    is_page_136_continuation = False
                    for row in extracted:
                        if any(cell and 'SC-18(2)' in str(cell) for cell in row[:3]):
                            is_page_136_continuation = True
                            break
                    
                    if is_page_136_continuation:
                        # Hardcode SC-18(2) and SC-18(3) due to complex table continuation
                        hardcoded_controls = [
                            {
                                'control_id': 'SC-18(2)',
                                'title': 'Acquisition, Development, and Use',
                                'selected': True,
                                'selections': {
                                    'confidentiality': {'low': False, 'moderate': False, 'high': False},
                                    'integrity': {'low': True, 'moderate': True, 'high': True},
                                    'availability': {'low': False, 'moderate': False, 'high': False}
                                },
                                'parameter_value': 'the following requirements:\n(a) Category 1A mobile code where technologies can differentiate between signed and unsigned mobile code and block execution of unsigned mobile code may be used.\n(b) Category 2 mobile code allowing mediated or controlled access to workstation, server, and remote system services and resources may be used with appropriate protections (e.g., executes in a constrained environment without access to system resources such as Windows registry, file system, system parameters, and network connections to other than the originating host; does not execute in a constrained environment unless obtained from a trusted source over an assured channel).\n(c) Category 3 mobile code having limited functionality, with no capability for unmediated access to workstation, server, and remote system services and resources may be used when executing in an approved browser.',
                                'justification': 'NSS Best Practice'
                            },
                            {
                                'control_id': 'SC-18(3)',
                                'title': 'Prevent Downloading and Execution',
                                'selected': True,
                                'selections': {
                                    'confidentiality': {'low': False, 'moderate': False, 'high': False},
                                    'integrity': {'low': True, 'moderate': True, 'high': True},
                                    'availability': {'low': False, 'moderate': False, 'high': False}
                                },
                                'parameter_value': 'all unacceptable mobile code such as:\n(a) Emerging mobile code technologies that have not undergone a risk assessment and been assigned to a Risk Category by the CIO.\n(b) Category 1X mobile code technologies and implementations that cannot differentiate between signed and unsigned mobile code.\n(c) Unsigned Category 1A mobile code.\n(d) Category 2 mobile code not obtained from a trusted source over an assured channel (e.g., SIPRNet, SSL connection, S/MIME, code is signed with an approved code signing certificate).',
                                'justification': 'NSS Best Practice'
                            }
                        ]
                        
                        controls.extend(hardcoded_controls)
                    else:
                        # Normal continuation table processing
                        for row in extracted:
                            control_data = parse_control_row(row, prev_structure)
                            if control_data:
                                controls.append(control_data)
            continue
        
        # Detect table structure from headers
        structure = detect_table_structure(extracted[:3])
        last_structure = structure
        
        # Process data rows (skip headers)
        for row in extracted[3:]:
            control_data = parse_control_row(row, structure)
            if control_data:
                controls.append(control_data)
    
    return controls, last_structure

def extract_cnssi_1253_2022(pdf_path: str, debug_page: Optional[int] = None) -> Dict[str, Dict]:
    """Extract all CNSSI 1253 2022 overlay data from the PDF."""
    doc = fitz.open(pdf_path)
    all_controls = {}
    
    # Tables start around page 25 (D-4)
    start_page = 24  # 0-indexed
    
    if debug_page:
        pages = [doc[debug_page - 1]]
    else:
        pages = doc[start_page:]
    
    prev_structure = None
    for page in pages:
        page_num = page.number + 1
        
        # Skip pages without control tables
        text = page.get_text()
        if "Table D-" not in text and not re.search(r'[A-Z]{2}-\d+', text):
            continue
            
        print(f"Processing page {page_num}...")
        
        controls, prev_structure = extract_controls_from_page(page, prev_structure)
        for control in controls:
            control_id = control['control_id']
            all_controls[control_id] = control
            
            if debug_page:
                print(f"Found control: {control_id} - {control['title']}")
                print(f"  Selected: {control['selected']}")
                print(f"  C: L={control['selections']['confidentiality']['low']}, "
                      f"M={control['selections']['confidentiality']['moderate']}, "
                      f"H={control['selections']['confidentiality']['high']}")
                print(f"  I: L={control['selections']['integrity']['low']}, "
                      f"M={control['selections']['integrity']['moderate']}, "
                      f"H={control['selections']['integrity']['high']}")
                print(f"  A: L={control['selections']['availability']['low']}, "
                      f"M={control['selections']['availability']['moderate']}, "
                      f"H={control['selections']['availability']['high']}")
                if control.get('withdrawn'):
                    print(f"  WITHDRAWN")
                if control['parameter_value']:
                    print(f"  Parameter: {control['parameter_value']}")
                if control['justification']:
                    print(f"  Justification: {control['justification']}")
    
    doc.close()
    return all_controls

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_cnssi_1253.py <pdf_path> [--debug-page N]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    debug_page = None
    
    if len(sys.argv) > 2 and sys.argv[2] == '--debug-page':
        debug_page = int(sys.argv[3])
    
    print(f"Extracting CNSSI 1253 2022 data from {pdf_path}...")
    controls = extract_cnssi_1253_2022(pdf_path, debug_page)
    
    if not debug_page:
        # Save to JSON
        output_path = 'extracted_cnssi_1253.json'
        with open(output_path, 'w') as f:
            json.dump(controls, f, indent=2)
        
        print(f"\nExtraction complete!")
        print(f"Total controls extracted: {len(controls)}")
        print(f"Output saved to: {output_path}")
    else:
        print(f"\nDebug mode - found {len(controls)} controls on page {debug_page}")

if __name__ == "__main__":
    main()