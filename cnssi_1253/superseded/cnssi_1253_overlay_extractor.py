#!/usr/bin/env python3
"""
CNSSI 1253 Overlay Control Extractor

This script extracts control parameter values from the CNSSI 1253 overlay PDF.
The PDF contains a table format with columns: ID, Control Text, and Defined Value for NSS.
"""

import fitz  # PyMuPDF
import json
import re
import sys
from typing import Dict, List, Tuple, Optional

class CNSSI1253Extractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.controls = {}
        self.debug_mode = False
        self.current_control_id = None
        self.current_control_elements = []
        
    def extract_controls(self) -> Dict:
        """Extract all controls from the PDF document."""
        try:
            doc = fitz.open(self.pdf_path)
            print(f"Processing {len(doc)} pages...")
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._process_page(page, page_num + 1)
            
            if self.current_control_elements:
                self._finalize_current_control(len(doc))
                
            doc.close()
            return self.controls
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return {}
    
    def _process_page(self, page, page_num: int):
        """Process a single page, handling controls that span multiple pages."""
        try:
            if self.debug_mode:
                print(f"\n=== Processing Page {page_num} ===")
            
            text_dict = page.get_text("dict")
            page_elements = self._extract_text_elements(text_dict, page_num)
            self._process_page_elements(page_elements, page_num)
                
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
    
    def _extract_text_elements(self, text_dict: dict, page_num: int) -> List[Dict]:
        """Extract text elements from a page."""
        text_elements = []
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            x0, y0, x1, y1 = bbox
                            
                            text_elements.append({
                                "text": text,
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1,
                                "font": span.get("font", ""),
                                "flags": span.get("flags", 0),
                                "page": page_num
                            })
        
        text_elements.sort(key=lambda x: (round(x["y0"], 1), x["x0"]))
        return text_elements
    
    def _process_page_elements(self, page_elements: List[Dict], page_num: int):
        """Process elements from a page, handling cross-page controls."""
        if self.debug_mode:
            print(f"    Analyzing {len(page_elements)} text elements on page {page_num}")
        
        control_ids_found = []
        for i, element in enumerate(page_elements):
            element_text = element["text"]
            
            enhancement_match = re.search(r'([A-Z]{2}-\d{1,2}\(\d+\))', element_text)
            base_control_match = re.search(r'\b([A-Z]{2}-\d{1,2})\b(?!\(\d+\))', element_text)
            
            if enhancement_match or base_control_match:
                found_id = enhancement_match.group(1) if enhancement_match else base_control_match.group(1)
                control_ids_found.append((i, found_id, element))
                
                if self.debug_mode:
                    control_type = "ENHANCEMENT" if enhancement_match else "BASE"
                    print(f"    Element {i}: Found {control_type} ID '{found_id}' in text: '{element_text}'")
        
        if self.debug_mode:
            print(f"    Found {len(control_ids_found)} control IDs on this page: {[cid[1] for cid in control_ids_found]}")
        
        # Handle continuation content
        if control_ids_found and control_ids_found[0][0] > 0 and self.current_control_id:
            continuation_elements = page_elements[:control_ids_found[0][0]]
            
            valid_continuation = []
            for elem in continuation_elements:
                elem_text = elem["text"].strip()
                if not (("CNSSI No. 1253" in elem_text) or 
                       ("Control Text" in elem_text) or
                       ("Defined Value for NSS" in elem_text) or
                       ("Table E-1" in elem_text) or
                       ("Appendix" in elem_text.upper()) or
                       (re.match(r'^[A-Z]-\d+$', elem_text)) or
                       (re.match(r'^\d+$', elem_text)) or
                       (len(elem_text) < 3)):
                    valid_continuation.append(elem)
            
            if valid_continuation:
                if self.debug_mode:
                    print(f"    Found {len(valid_continuation)} continuation elements for control {self.current_control_id}")
                
                for elem in valid_continuation:
                    elem["is_continuation"] = True
                self.current_control_elements.extend(valid_continuation)
        
        # Process control IDs
        for i, (element_index, control_id, control_element) in enumerate(control_ids_found):
            if self.debug_mode:
                print(f"    Processing control {i+1}/{len(control_ids_found)}: {control_id}")
            
            if self.current_control_id and self.current_control_id != control_id:
                if self.debug_mode:
                    print(f"    Finalizing previous control {self.current_control_id}")
                self._finalize_current_control(page_num)
            
            end_index = len(page_elements)
            if i + 1 < len(control_ids_found):
                end_index = control_ids_found[i + 1][0]
            
            control_elements = page_elements[element_index:end_index]
            
            if self.current_control_id == control_id:
                self.current_control_elements.extend(control_elements)
            else:
                self.current_control_id = control_id
                self.current_control_elements = control_elements
        
        # Handle pages with no control IDs
        if not control_ids_found and self.current_control_id:
            valid_elements = []
            for elem in page_elements:
                elem_text = elem["text"].strip()
                if not (("CNSSI No. 1253" in elem_text) or 
                       ("Control Text" in elem_text) or
                       ("Defined Value for NSS" in elem_text) or
                       (len(elem_text) < 3)):
                    valid_elements.append(elem)
            
            if valid_elements:
                self.current_control_elements.extend(valid_elements)
    
    def _finalize_current_control(self, last_page: int):
        """Finalize the current control and add it to the results."""
        if not self.current_control_id or not self.current_control_elements:
            return
        
        try:
            if self.debug_mode:
                print(f"    Finalizing control {self.current_control_id} with {len(self.current_control_elements)} elements")
            
            control_data = self._parse_control_group(self.current_control_elements, last_page)
            
            if control_data:
                control_id = control_data["id"]
                
                if control_id not in self.controls:
                    self.controls[control_id] = {
                        "control_text": control_data["control_text"],
                        "defined_value": control_data["defined_value"]
                    }
                    
                    if self.debug_mode:
                        print(f"  ✓ Added NEW control {control_id}")
                else:
                    existing = self.controls[control_id]
                    
                    if control_data["control_text"] and control_data["control_text"].strip():
                        if existing["control_text"]:
                            existing["control_text"] = (existing["control_text"] + " " + control_data["control_text"]).strip()
                        else:
                            existing["control_text"] = control_data["control_text"]
                    
                    if control_data["defined_value"] and control_data["defined_value"].strip():
                        if existing["defined_value"]:
                            existing["defined_value"] = (existing["defined_value"] + " " + control_data["defined_value"]).strip()
                        else:
                            existing["defined_value"] = control_data["defined_value"]
            
        except Exception as e:
            print(f"Error finalizing control {self.current_control_id}: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
        
        self.current_control_id = None
        self.current_control_elements = []
    
    def _parse_control_group(self, elements: List[Dict], page_num: int) -> Optional[Dict]:
        """Parse a group of elements that belong to one control."""
        if not elements:
            return None
        
        original_elements = [elem for elem in elements if not elem.get("is_continuation", False)]
        continuation_elements = [elem for elem in elements if elem.get("is_continuation", False)]
        
        original_elements.sort(key=lambda x: (round(x["y0"], 1), x["x0"]))
        continuation_elements.sort(key=lambda x: (round(x["y0"], 1), x["x0"]))
        
        sorted_elements = original_elements + continuation_elements
        
        full_text = " ".join([elem["text"] for elem in sorted_elements])
        
        enhancement_match = re.search(r'([A-Z]{2}-\d{1,2}\(\d+\))', full_text)
        base_control_match = re.search(r'\b([A-Z]{2}-\d{1,2})\b(?!\(\d+\))', full_text)
        
        if enhancement_match:
            control_id = enhancement_match.group(1)
        elif base_control_match:
            control_id = base_control_match.group(1)
        else:
            return None
        
        control_text_elements = []
        defined_value_elements = []
        
        for elem in sorted_elements:
            elem_text = elem["text"].strip()
            
            if (("Control Text" in elem_text) or 
                ("Defined Value for NSS" in elem_text) or
                ("CNSSI No. 1253" in elem_text) or
                (re.match(r'^[A-Z]-\d+$', elem_text))):
                continue
            
            x_pos = elem["x0"]
            
            # Better content detection for defined values
            is_defined_value = (
                elem_text.startswith("Not appropriate to define") or
                elem_text.startswith("At least annually") or
                elem_text.startswith("Not to exceed") or
                elem_text.startswith("all NSS") or
                elem_text.startswith("all organizations operating NSS") or
                elem_text in ["All", "Disables", "3", "15 minutes", "30 minutes"]
            )
            
            if x_pos < 80:
                continue
            elif x_pos < 300 and not is_defined_value:
                control_text_elements.append(elem)
            else:
                defined_value_elements.append(elem)
        
        control_text_elements.sort(key=lambda x: sorted_elements.index(x))
        defined_value_elements.sort(key=lambda x: sorted_elements.index(x))
        
        control_text = " ".join([elem["text"] for elem in control_text_elements]).strip()
        defined_value = " ".join([elem["text"] for elem in defined_value_elements]).strip()
        
        if control_id in control_text:
            control_text = control_text.replace(control_id, "").strip()
        
        return {
            "id": control_id,
            "control_text": control_text,
            "defined_value": defined_value
        }
    
    def save_to_json(self, output_file: str):
        """Save extracted controls to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.controls, f, indent=2, ensure_ascii=False)
            print(f"\nSuccessfully saved {len(self.controls)} controls to {output_file}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")
    
    def print_summary(self):
        """Print a summary of extracted controls."""
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Total controls extracted: {len(self.controls)}")
        
        if not self.controls:
            print("No controls found!")
            return
        
        families = {}
        enhancements = 0
        base_controls = 0
        
        for control_id in self.controls.keys():
            family = control_id.split('-')[0]
            families[family] = families.get(family, 0) + 1
            
            if '(' in control_id:
                enhancements += 1
            else:
                base_controls += 1
        
        print(f"Base controls: {base_controls}")
        print(f"Control enhancements: {enhancements}")
        
        print("\nControls by family:")
        for family, count in sorted(families.items()):
            print(f"  {family}: {count} controls")
        
        print("\nFirst 5 controls found:")
        for i, (control_id, control_info) in enumerate(list(self.controls.items())[:5]):
            print(f"\n  {control_id}:")
            control_text = control_info.get("control_text", "")
            defined_value = control_info.get("defined_value", "")
            
            print(f"    Control Text: {control_text[:100]}..." if len(control_text) > 100 else f"    Control Text: {control_text}")
            print(f"    Defined Value: {defined_value[:100]}..." if len(defined_value) > 100 else f"    Defined Value: {defined_value}")
                
        print(f"\n... and {len(self.controls) - 5} more controls" if len(self.controls) > 5 else "")
    
    def debug_page(self, page_num: int):
        """Debug a specific page."""
        try:
            doc = fitz.open(self.pdf_path)
            if page_num <= len(doc):
                page = doc[page_num - 1]
                
                print(f"\n=== DEBUG PAGE {page_num} ===")
                
                text_dict = page.get_text("dict")
                page_elements = self._extract_text_elements(text_dict, page_num)
                
                print(f"Found {len(page_elements)} text elements:")
                for i, element in enumerate(page_elements[:20]):
                    print(f"  Element {i}: '{element['text'][:50]}...' at ({element['x0']:.1f}, {element['y0']:.1f})")
                    
                    enhancement_match = re.search(r'([A-Z]{2}-\d{1,2}\(\d+\))', element['text'])
                    base_control_match = re.search(r'\b([A-Z]{2}-\d{1,2})\b(?!\(\d+\))', element['text'])
                    
                    if enhancement_match or base_control_match:
                        found_id = enhancement_match.group(1) if enhancement_match else base_control_match.group(1)
                        control_type = "ENHANCEMENT" if enhancement_match else "BASE"
                        print(f"    → Found {control_type} control ID: {found_id}")
            
            doc.close()
            
        except Exception as e:
            print(f"Error debugging page: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python cnssi_1253_extractor.py <pdf_file> [--debug-page N]")
        print("Example: python cnssi_1253_extractor.py cnssi_1253_overlay.pdf")
        print("Example: python cnssi_1253_extractor.py cnssi_1253_overlay.pdf --debug-page 3")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    if len(sys.argv) == 4 and sys.argv[2] == "--debug-page":
        try:
            debug_page_num = int(sys.argv[3])
            extractor = CNSSI1253Extractor(pdf_file)
            extractor.debug_mode = True
            extractor.debug_page(debug_page_num)
            return
        except ValueError:
            print("Invalid page number for debug mode")
            sys.exit(1)
    
    output_file = "extracted_cnssi_1253_overlay.json"
    
    print("CNSSI 1253 Overlay Control Extractor")
    print("=" * 40)
    
    extractor = CNSSI1253Extractor(pdf_file)
    extractor.debug_mode = True
    
    controls = extractor.extract_controls()
    
    if controls:
        extractor.save_to_json(output_file)
        extractor.print_summary()
    else:
        print("No controls were extracted.")
        print("Try using --debug-page N to see the content details.")

if __name__ == "__main__":
    main()