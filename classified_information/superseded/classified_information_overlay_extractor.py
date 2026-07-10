#!/usr/bin/env python3
"""
Classified Information Overlay Control Extractor

Extracts control and enhancement information from the Classified Information Overlay PDF.
Outputs a JSON file with all controls, enhancements, and their attributes.

Usage:f
    python classified_information_overlay_extractor.py <pdf_file>
    python classified_information_overlay_extractor.py <pdf_file> --debug-page N
    python classified_information_overlay_extractor.py <pdf_file> --search-9
"""

import fitz  # PyMuPDF for PDF parsing
import json
import re
import sys
from typing import Dict, List

class ClassifiedControlExtractor:
    """
    Extracts controls and enhancements from a classified overlay PDF.
    """
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.controls = {}  # All extracted controls
        self.current_control = None  # Current control/enhancement being processed
        self.current_base_control = None  # Current base control (e.g., "AC-3")
        self.current_attribute = None  # Current attribute being appended to

    def extract_controls(self) -> Dict:
        """
        Extract all controls and enhancements from the PDF.
        """
        try:
            doc = fitz.open(self.pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._process_page(page, page_num + 1)
            doc.close()
            return self.controls
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return {}

    def _process_page(self, page, page_num: int):
        """
        Process a single PDF page: extract formatted text and parse controls/attributes.
        """
        try:
            text_dict = page.get_text("dict")
            formatted_text = self._extract_formatted_text(text_dict)
            self._find_controls_and_attributes(formatted_text, page_num)
        except Exception as e:
            pass

    def _extract_formatted_text(self, text_dict: dict) -> List[dict]:
        """
        Extract lines of text with formatting (bold, font, etc.) from a PDF text dict.
        Skips footers and page numbers.
        """
        formatted_text = []
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    line_text = ""
                    line_formats = []
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        flags = span.get("flags", 0)
                        line_text += text
                        line_formats.append({
                            "text": text,
                            "bold": bool(flags & 16),
                            "font": span.get("font", ""),
                            "flags": flags
                        })
                    if line_text.strip():
                        # Skip footers and page numbers
                        stripped = line_text.strip()
                        if (stripped == "Classified Information Overlay" or
                            stripped.isdigit() or
                            stripped == "May 9, 2014"):
                            continue
                        formatted_text.append({
                            "text": stripped,
                            "formats": line_formats
                        })
        return formatted_text

    def _flexible_enhancement_match(self, line_text: str):
        """
        Match enhancement lines like 'Control Enhancement: 4, 5, 6' with flexible patterns.
        """
        patterns = [
            r'^Control Enhancement:\s*(\d+(?:,\s*\d+)*)$',
            r'^Control\s+Enhancement:\s*(\d+(?:,\s*\d+)*)$',
            r'^Control\s*Enhancement\s*:\s*(\d+(?:,\s*\d+)*)$',
            r'^Control Enhancement\s*:\s*(\d+(?:,\s*\d+)*).*$',
            r'^Control Enhancement\s*:\s*(\d+(?:,\s*\d+)*)\s*$'
        ]
        for pattern in patterns:
            match = re.match(pattern, line_text, re.IGNORECASE)
            if match:
                return match
        return None

    def _find_controls_and_attributes(self, formatted_text: List[dict], page_num: int):
        """
        Parse formatted lines to find controls, enhancements, and their attributes.
        """
        for line_data in formatted_text:
            line_text = line_data["text"]
            formats = line_data["formats"]
            is_bold = any(fmt.get("bold", False) for fmt in formats)
            # Base control: e.g., "AC-3, ACCESS ENFORCEMENT"
            base_control_match = re.match(r'^([A-Z]{2}-\d{1,2}),?\s*(.+)$', line_text)
            enhancement_match = self._flexible_enhancement_match(line_text)
            if base_control_match and is_bold:
                control_id = base_control_match.group(1)
                control_name = base_control_match.group(2).strip()
                self.current_control = control_id
                self.current_base_control = control_id
                self.current_attribute = None
                self.controls[control_id] = {
                    "name": control_name,
                    "attributes": {},
                    "page": page_num
                }
                continue
            elif enhancement_match:
                if self.current_base_control:
                    enhancement_numbers = enhancement_match.group(1).split(',')
                    for enhancement_num in enhancement_numbers:
                        enhancement_num = enhancement_num.strip()
                        enhancement_id = f"{self.current_base_control}({enhancement_num})"
                        base_name = self.controls.get(self.current_base_control, {}).get("name", "")
                        self.controls[enhancement_id] = {
                            "name": base_name,
                            "attributes": {},
                            "page": page_num
                        }
                    self.current_control = f"{self.current_base_control}({enhancement_numbers[-1].strip()})"
                    self.current_attribute = None
                continue
            # Attribute line: e.g., "Justification to Select: ..."
            if self.current_control and ':' in line_text:
                attribute_result = self._extract_attribute_from_line(line_text)
                if attribute_result:
                    attr_name, attr_content = attribute_result
                    # Append or set attribute
                    attrs = self.controls[self.current_control]["attributes"]
                    if attr_name in attrs:
                        attrs[attr_name] += " " + attr_content.strip()
                    else:
                        attrs[attr_name] = attr_content.strip()
                        self.current_attribute = attr_name
                    continue
            # Continuation of previous attribute
            elif self.current_control and self.current_attribute and line_text.strip():
                if not (base_control_match or enhancement_match or self._extract_attribute_from_line(line_text)):
                    attrs = self.controls[self.current_control]["attributes"]
                    attrs[self.current_attribute] += " " + line_text.strip()

    def _extract_attribute_from_line(self, line_text: str):
        """
        If line starts with a known attribute, return (attribute_name, content).
        """
        known_attributes = [
            "Justification to Select",
            "Supplemental Guidance",
            "Parameter Value(s)",
            "Parameter Value",
            "Regulatory/Statutory Reference(s)",
            "Control Extension",
            "Control Extension(s)",
            "Control Extension and Parameter Value(s)"
        ]
        for attr in known_attributes:
            if line_text.startswith(attr + ":"):
                content = line_text[len(attr) + 1:].strip()
                return attr, content
        return None

    def save_to_json(self, output_file: str):
        """
        Save extracted controls to a JSON file.
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.controls, f, indent=2, ensure_ascii=False)
            print(f"\nSaved {len(self.controls)} controls to {output_file}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")

    def print_summary(self):
        """
        Print a summary of extracted controls and enhancements.
        """
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
        print("\nFirst 10 controls found:")
        for i, (control_id, control_info) in enumerate(list(self.controls.items())[:10]):
            print(f"  {control_id}: {control_info['name']}")
            if control_info['attributes']:
                print(f"    Attributes: {list(control_info['attributes'].keys())}")
            else:
                print(f"    Attributes: None found")

def main():
    if len(sys.argv) < 2:
        print("Usage: python classified_information_overlay_extractor.py <pdf_file>")
        sys.exit(1)
    pdf_file = sys.argv[1]
    output_file = "extracted_classified_information_overlay.json"
    print("Classified Information Overlay Control Extractor\n" + "=" * 50)
    extractor = ClassifiedControlExtractor(pdf_file)
    controls = extractor.extract_controls()
    if controls:
        extractor.save_to_json(output_file)
        extractor.print_summary()
    else:
        print("No controls were extracted.")

if __name__ == "__main__":
    main()