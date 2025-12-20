# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a web application for viewing and managing security control overlays that constitute IL6 (Information Level 6) — the DoD standard for cloud service providers working with classified secret information. It displays NIST SP 800-53 controls with security overlays including FedRAMP High, CNSSI 1253, Classified Information Overlay, and FedRAMP+.

## Architecture

- **Frontend**: Single-page application using vanilla JavaScript embedded in `index.html` (no build process)
- **Data Pipeline**: Python scripts extract data from PDF overlays → JSON files → JavaScript web app
- **Hosting**: https://il6.sl5taskforce.org/ (GitHub: https://github.com/SL5TaskForce/IL6-control-catalog)

## Common Development Commands

### Python Data Extraction
```bash
# Extract overlay data from PDFs (requires PyMuPDF/fitz)
python cnssi_1253/extract_cnssi_1253.py cnssi_1253/CNSSI_1253_2022.pdf
python classified_information/extract_classified_information.py classified_information/classified_information_overlay_2022.pdf

# Debug specific pages
python cnssi_1253/extract_cnssi_1253.py cnssi_1253/CNSSI_1253_2022.pdf --debug-page 10

# Sort NIST controls naturally
python nist_catalog/nist_sorter.py input.json output.json
```

### Development
- No build process - edit `index.html` directly
- No package manager - pure vanilla JavaScript
- Deploy by pushing to GitHub

## Code Structure

### Frontend (`index.html`)
- **Data Loading**: `loadData()` fetches all JSON files
- **Rendering**: `renderControls()` displays filtered controls
- **State**: Global variables store control data and overlay states
- **Events**: Toggle overlays, search, filter by family, expand/collapse controls

### Data Pipeline
Each overlay directory contains:
- PDF source document
- Python extractor script (`extract_*.py`)
- Generated JSON data file
- Common pattern: PDF → Python extractor → JSON → Web app

### Key Data Structures
```javascript
// Control format
{
  "id": "AC-1",
  "text": "Control description...",
  "family": "Access Control",
  "enhancements": [...],
  "discussion": "..."
}

// Overlay format varies by type
// FedRAMP: {"assessment_procedures": [...]}
// CNSSI: {"selections": {...}, "parameter_value": "...", "justification": "..."}
// Classified: {"justification": "...", "parameter_value": "...", "guidance": "..."}
```

## Important Patterns

1. **Control ID Format**: `[A-Z]{2}-\d{1,2}` (base) or `[A-Z]{2}-\d{1,2}\(\d+\)` (enhancement)
2. **Overlay Toggle Logic**: Each overlay can be enabled/disabled, affecting control visibility
3. **Enhancement Display**: Controls with enhancements have expandable sections
4. **Modal System**: Click control IDs to preview in modal
5. **Natural Sorting**: Controls sorted as AC-1, AC-2, ..., AC-10 (not lexically)

## Adding New Overlays

1. Create directory for new overlay
2. Add PDF source document
3. Create Python extractor following existing patterns (see `cnssi_1253/extract_cnssi_1253.py` as template)
4. Generate JSON data
5. Add overlay loading in `loadData()` function
6. Add toggle UI in overlay panel
7. Update `getOverlayInfo()` to handle new overlay format

## Testing

No automated tests exist. Manual testing process:
1. Run Python extractors on PDFs
2. Verify JSON output structure
3. Load in browser and test filtering/toggling
4. Check control display and enhancements
5. Test search functionality

## Dependencies

- **Python**: PyMuPDF (fitz) for PDF extraction
- **JavaScript**: None (vanilla JS only)
- **Deployment**: GitHub Pages