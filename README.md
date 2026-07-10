# IL6 Control Catalog

An interactive web application for exploring security control overlays that constitute **Information Level 6 (IL6)**, the DoD standard for cloud service providers working with classified secret information.

🌐 **Live Site:** [https://il6.sl5taskforce.org/](https://il6.sl5taskforce.org/)

---

## Overview

IL6 is based on the **NIST SP 800-53** control catalog and is defined as the union of multiple security overlays:

| Overlay | Description | Precedence |
|---------|-------------|------------|
| **FedRAMP High** | Federal Risk and Authorization Management Program baseline | Lowest |
| **CNSSI 1253** | Committee on National Security Systems security categorization | ↑ |
| **Classified Information Overlay** | Additional controls for classified environments | ↑ |
| **FedRAMP+** | DoD-specific enhancements to FedRAMP | Highest |

Where overlays disagree, each takes precedence over the ones below it.

---

## Features

- 📋 **Complete NIST SP 800-53 Control Catalog** — Browse all controls and enhancements
- 🏷️ **Overlay Badges** — Instantly see which overlays apply to each control
- 🔍 **Search & Filter** — Find controls by ID, name, or text; filter by control family
- 👁️ **Show/Hide Unselected** — Focus on controls with active overlays or see everything
- 📖 **Detailed Views** — Expand controls to see full text, discussions, related controls, and overlay-specific parameters
- 🔗 **NIST Links** — Direct links to official NIST documentation for each control
- 📱 **Responsive Design** — Works on desktop and mobile

---

## Quick Start

Simply open `index.html` in a web browser — no build process or server required.

```bash
# Clone the repository
git clone https://github.com/securitylevel5/il6-control-catalog.git
cd IL6-control-catalog

# Open in browser
open index.html      # macOS
start index.html     # Windows
xdg-open index.html  # Linux
```

Or serve locally:

```bash
python -m http.server 8000
# Visit http://localhost:8000
```

---

## Project Structure

```
control-overlays-selector/
├── index.html                    # Main web application (vanilla JS)
├── CLAUDE.md                     # AI assistant guidance
├── README.md                     # This file
│
├── nist_catalog/                 # NIST SP 800-53 source data
│   ├── nist_sp_800-53_control_catalog.json
│   └── nist_sorter.py
│
├── fedramp_high/                 # FedRAMP High overlay
│   └── extracted_fedramp_high_overlay.json
│
├── fedramp_plus/                 # FedRAMP+ overlay
│   ├── fedramp_plus_overlay.pdf
│   └── extracted_fedramp_plus_overlay.json
│
├── cnssi_1253/                   # CNSSI 1253 overlay
│   ├── CNSSI_1253_2022.pdf
│   ├── extract_cnssi_1253.py
│   └── extracted_cnssi_1253.json
│
└── classified_information/       # Classified Information overlay
    ├── classified_information_overlay_2022.pdf
    ├── extract_classified_information.py
    └── extracted_classified_information.json
```

---

## Data Pipeline

The application uses a PDF → JSON → Web pipeline:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   PDF Source    │ ──►  │  Python Script  │ ──►  │   JSON Data     │
│   Documents     │      │   (extraction)  │      │   (structured)  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  Web App (JS)   │
                                                  │  index.html     │
                                                  └─────────────────┘
```

### Extracting Data from PDFs

```bash
# Requires PyMuPDF (fitz)
pip install PyMuPDF

# Extract CNSSI 1253 overlay
python cnssi_1253/extract_cnssi_1253.py cnssi_1253/CNSSI_1253_2022.pdf

# Extract Classified Information overlay
python classified_information/extract_classified_information.py \
    classified_information/classified_information_overlay_2022.pdf

# Debug specific pages
python cnssi_1253/extract_cnssi_1253.py cnssi_1253/CNSSI_1253_2022.pdf --debug-page 10
```

---

## Development

### No Build Required

This is a vanilla JavaScript application with zero dependencies. Edit `index.html` directly and refresh your browser.

### Key Functions

| Function | Purpose |
|----------|---------|
| `loadData()` | Fetches all JSON files on page load |
| `renderControls()` | Displays filtered controls |
| `getOverlayInfo(controlId)` | Returns overlays applicable to a control |
| `renderOverlay(overlay)` | Renders overlay details |

### Data Structures

**Control Format:**
```javascript
{
  "id": "AC-1",
  "name": "Policy and Procedures",
  "text": "Control description...",
  "family": "AC",
  "discussion": "...",
  "relatedControls": ["AC-2", "PM-9"],
  "isEnhancement": false
}
```

**Overlay Formats vary by type:**
```javascript
// FedRAMP: Assessment procedures
{ "assessment_procedures": [...] }

// CNSSI: CIA selections
{ "selections": { "confidentiality": {...}, "integrity": {...}, "availability": {...} } }

// Classified: Justification and parameters
{ "justification": "...", "parameter_value": "..." }
```

---

## Adding a New Overlay

1. **Create directory** for the new overlay
2. **Add PDF source** document
3. **Create Python extractor** (see existing extractors as templates)
4. **Generate JSON** data file
5. **Update `loadData()`** in `index.html` to load the new JSON
6. **Add overlay toggle** in the UI (if needed)
7. **Update `getOverlayInfo()`** to handle the new overlay format

---

## Deployment

The site is deployed at [https://il6.sl5taskforce.org/](https://il6.sl5taskforce.org/). Push to the main branch to trigger deployment.

---

## Dependencies

| Component | Dependency |
|-----------|------------|
| **Web App** | None (vanilla JavaScript) |
| **PDF Extraction** | Python 3, PyMuPDF (`pip install PyMuPDF`) |
| **Deployment** | GitHub Pages |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test your changes locally
4. Submit a merge request

---

## License

Created by **[Security Level 5](https://sl5.org)** for the security community.

The code is licensed under the [MIT License](LICENSE). The NIST SP 800-53 and
FedRAMP control text presented by this catalog is a work of the United States
Government and is in the public domain (17 U.S.C. § 105).

---

## Related Resources

- [NIST SP 800-53 Rev 5](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) — Security and Privacy Controls
- [FedRAMP](https://www.fedramp.gov/) — Federal Risk and Authorization Management Program
- [CNSSI 1253](https://www.cnss.gov/CNSS/issuances/Instructions.cfm) — Security Categorization and Control Selection
- [DoD Cloud Computing SRG](https://public.cyber.mil/dccs/) — Defense Information Systems Agency Cloud Security

