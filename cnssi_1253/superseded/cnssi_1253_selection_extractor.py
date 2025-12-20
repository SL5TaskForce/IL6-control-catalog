#!/usr/bin/env python3
"""
CNSSI 1253 PDF Parser
Extracts security controls from CNSSI-1253 PDF and converts to JSON format.
"""

import json
import re
import sys
from typing import Dict, List, Optional
import fitz  # PyMuPDF


class CNSSIParser:
    def __init__(self, pdf_path: str, debug: bool = False):
        self.pdf_path = pdf_path
        self.doc = None
        self.controls = []
        self.debug = debug
        
    def open_pdf(self):
        """Open the PDF document."""
        try:
            self.doc = fitz.open(self.pdf_path)
            print(f"Successfully opened PDF: {self.pdf_path}")
            print(f"Total pages: {len(self.doc)}")
        except Exception as e:
            print(f"Error opening PDF: {e}")
            sys.exit(1)
    
    def close_pdf(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
    
    def is_table_header_row(self, text_line: str) -> bool:
        """Check if a line contains table headers."""
        text_upper = text_line.upper()
        
        if 'ID' in text_upper and 'TITLE' in text_upper:
            return True
        if 'CONFIDENTIALITY' in text_upper and 'INTEGRITY' in text_upper:
            return True
        if 'AVAILABILITY' in text_upper:
            return True
        if text_line.strip() == 'L M H L M H L M H':
            return True
        if 'L M H' in text_line and text_line.count('L M H') >= 2:
            return True
        
        # Also look for the start of actual control data
        control_id = self.extract_control_id(text_line)
        if control_id == 'AC-1':  # First control is usually AC-1
            return True
            
        return False
    
    def extract_control_id(self, text: str) -> Optional[str]:
        """Extract control ID from text (e.g., AC-1, AC-2(1))."""
        text_stripped = text.strip()
        
        # Match patterns like AC-1, AC-2(1), PM-1, etc.
        pattern = r'^([A-Z]{2,3}-\d+(?:\(\d+\))?)'
        match = re.search(pattern, text_stripped)
        if match:
            return match.group(1)
        
        # Alternative pattern - look anywhere in the text
        pattern2 = r'([A-Z]{2,3}-\d+(?:\(\d+\))?)'
        match = re.search(pattern2, text)
        if match:
            start_pos = match.start()
            if start_pos == 0 or text[start_pos-1].isspace():
                return match.group(1)
        
        return None
    
    def has_selection_markers(self, text: str) -> bool:
        """Check if text contains X or + markers indicating selection."""
        pattern = r'(?:^|\s)([X+])(?:\s|$)'
        matches = re.findall(pattern, text)
        return len(matches) > 0
    
    def clean_title(self, title: str) -> str:
        """Clean and normalize control title."""
        # Remove extra whitespace and normalize
        title = ' '.join(title.split())
        # Remove any trailing markers that might have been included
        title = re.sub(r'\s*[X+]\s*$', '', title)
        return title.strip()
    
    def is_only_markers(self, text: str) -> bool:
        """Check if line contains only X, +, or whitespace."""
        pattern = r'^[X+\s]*$'
        return re.match(pattern, text) is not None
    
    def is_footnote_or_header(self, text: str) -> bool:
        """Check if text is a footnote, header, or other non-control content."""
        text_lower = text.lower()
        text_stripped = text.strip()
        
        # Check if it's just a number
        if text_stripped.isdigit():
            return True
        
        # Check for specific footnote text
        if 'changes to the security control catalog' in text_lower:
            return True
        if 'under the authority of nist' in text_lower:
            return True
        if 'cnssi no.' in text_lower:
            return True
        if 'appendix' in text_lower:
            return True
            
        # Check for page numbers like D-1, D-35
        if text.startswith('D-') and len(text) < 10:
            return True
            
        # Very short text
        if len(text_stripped) < 3:
            return True
            
        # Pure number check
        number_pattern = r'^\d+$'
        if re.match(number_pattern, text_stripped):
            return True
            
        return False
    
    def should_continue_control_title(self, text: str, current_control_id: str) -> bool:
        """Determine if text should be added to current control's title."""
        if self.is_footnote_or_header(text):
            return False
        
        # Don't continue if we hit another control ID
        if self.extract_control_id(text):
            return False
        
        # Don't continue if it's only selection markers
        if self.is_only_markers(text):
            return False
        
        # Don't continue if it looks like table structure
        if 'Confidentiality' in text or 'Integrity' in text or 'Availability' in text:
            return False
        
        return True
    
    def extract_controls_from_page(self, page_num: int) -> List[Dict]:
        """Extract controls from a single page."""
        page = self.doc[page_num]
        text = page.get_text()
        lines = text.split('\n')
        
        controls = []
        in_table = False
        current_control = None
        found_first_content_after_header = False
        
        print(f"  Page {page_num + 1} has {len(lines)} lines")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Debug output
            if self.debug and page_num < 3 and i < 50:
                display_line = line[:100] + '...' if len(line) > 100 else line
                print(f"    Line {i}: '{display_line}'")
            
            # Check if we're entering a table or if we find a control
            control_id = self.extract_control_id(line)
            
            if self.is_table_header_row(line):
                print(f"    Found table header at line {i}: {line}")
                in_table = True
                found_first_content_after_header = False
                continue
            
            # If we find a control ID, we're definitely in the table area
            if control_id:
                in_table = True
                if self.debug:
                    print(f"    Found control ID (auto-detected table): {control_id}")
            
            if not in_table:
                continue
            
            # Handle the first meaningful content after table headers on a new page
            if in_table and not found_first_content_after_header and not control_id:
                # This might be a continuation from the previous page
                if not self.is_footnote_or_header(line) and not self.is_only_markers(line):
                    cleaned_line = self.clean_title(line)
                    if cleaned_line:
                        # Create a continuation control that will be merged later
                        continuation_control = {
                            'id': 'CONTINUATION',
                            'name': cleaned_line,
                            'selected': self.has_selection_markers(line)
                        }
                        controls.append(continuation_control)
                        if self.debug:
                            print(f"    Found continuation text: '{cleaned_line}'")
                        found_first_content_after_header = True
                        continue
            
            if control_id:
                found_first_content_after_header = True
                
                # Save previous control if exists
                if current_control and current_control['name']:
                    controls.append(current_control)
                    if self.debug:
                        control_name = current_control['name'][:50] + '...' if len(current_control['name']) > 50 else current_control['name']
                        print(f"      Saved control: {current_control['id']} - {control_name} (Selected: {current_control['selected']})")
                
                # Start new control
                current_control = {
                    'id': control_id,
                    'name': '',
                    'selected': False
                }
                
                if self.debug:
                    print(f"    Processing control ID: {control_id}")
                
                # Check if there's title text on the same line after the ID
                remaining = line[len(control_id):].strip()
                if remaining and not self.is_only_markers(remaining):
                    current_control['name'] = self.clean_title(remaining)
                
                # Check for selection markers on this line
                if self.has_selection_markers(line):
                    current_control['selected'] = True
                    
            elif current_control:
                found_first_content_after_header = True
                
                # Check if this text should be added to the current control
                if self.should_continue_control_title(line, current_control['id']):
                    # Add to current control's name
                    cleaned_line = self.clean_title(line)
                    if cleaned_line:  # Only add if there's meaningful content
                        if current_control['name']:
                            current_control['name'] += ' ' + cleaned_line
                        else:
                            current_control['name'] = cleaned_line
                
                # Check for selection markers on this line
                if self.has_selection_markers(line):
                    current_control['selected'] = True
            
            else:
                # Look for selection markers even without a current control
                if controls and self.has_selection_markers(line):
                    controls[-1]['selected'] = True
        
        # Save the last control if exists
        if current_control and current_control['name']:
            controls.append(current_control)
            if self.debug:
                control_name = current_control['name'][:50] + '...' if len(current_control['name']) > 50 else current_control['name']
                print(f"      Saved final control: {current_control['id']} - {control_name} (Selected: {current_control['selected']})")
        
        print(f"  Extracted {len(controls)} controls from page {page_num + 1}")
        return controls
    
    def merge_continuation_controls(self, all_controls: List[Dict]) -> List[Dict]:
        """Merge controls that continue across pages."""
        merged_controls = []
        
        for i, control in enumerate(all_controls):
            if self.debug:
                print(f"Processing control for merge: {control.get('id', 'NO_ID')} - {control.get('name', 'NO_NAME')[:30]}...")
            
            # Check if this is a continuation control
            if control.get('id') == 'CONTINUATION':
                if merged_controls:
                    # Append to the last control's name
                    last_control = merged_controls[-1]
                    old_name = last_control['name']
                    last_control['name'] += ' ' + control['name']
                    if self.debug:
                        print(f"  Merged continuation: '{old_name}' + '{control['name']}' = '{last_control['name']}'")
                    
                    # Update selection status if needed
                    if control.get('selected'):
                        last_control['selected'] = True
                else:
                    if self.debug:
                        print(f"  Warning: Found CONTINUATION control but no previous control to merge with")
            else:
                # Regular control, just add it
                merged_controls.append(control)
        
        return merged_controls
    
    def parse_document(self) -> List[Dict]:
        """Parse the entire document and extract all controls."""
        if not self.doc:
            self.open_pdf()
        
        all_controls = []
        
        # Process each page
        for page_num in range(len(self.doc)):
            print(f"Processing page {page_num + 1}...")
            page_controls = self.extract_controls_from_page(page_num)
            all_controls.extend(page_controls)
        
        # Merge controls that span across pages
        merged_controls = self.merge_continuation_controls(all_controls)
        
        # Filter to only include selected controls and remove the selected field
        selected_controls = []
        for control in merged_controls:
            if (control.get('id') and 
                control['id'] != 'CONTINUATION' and 
                control.get('name') and 
                control.get('selected', False)):  # Only include if selected is True
                selected_controls.append({
                    'id': control['id'],
                    'name': control['name']
                    # Note: 'selected' field is intentionally omitted
                })
        
        self.controls = selected_controls
        return selected_controls
    
    def save_to_json(self, output_path: str):
        """Save the extracted controls to a JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.controls, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved {len(self.controls)} controls to {output_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")
    
    def print_summary(self):
        """Print a summary of extracted controls."""
        total = len(self.controls)
        
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Selected controls extracted: {total}")
        
        if total > 0:
            print(f"\nFirst 5 selected controls:")
            for i, control in enumerate(self.controls[:5]):
                name_display = control['name'][:60] + '...' if len(control['name']) > 60 else control['name']
                print(f"  ✓ {control['id']}: {name_display}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python cnssi_parser.py <input_pdf_path> <output_json_path> [--debug]")
        print("Example: python cnssi_parser.py cnssi_1253_selection.pdf controls.json")
        print("         python cnssi_parser.py cnssi_1253_selection.pdf controls.json --debug")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    json_path = sys.argv[2]
    debug = '--debug' in sys.argv
    
    print("CNSSI 1253 PDF Parser")
    print("=" * 50)
    
    parser = CNSSIParser(pdf_path, debug=debug)
    
    try:
        controls = parser.parse_document()
        parser.save_to_json(json_path)
        parser.print_summary()
        
    except Exception as e:
        print(f"Error during parsing: {e}")
        sys.exit(1)
    
    finally:
        parser.close_pdf()
    
    print(f"\n✓ Parsing completed successfully!")
    print(f"  Input:  {pdf_path}")
    print(f"  Output: {json_path}")


if __name__ == "__main__":
    main()