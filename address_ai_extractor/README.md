# Google GenAI Address Extraction for Odoo 20

A modern custom Odoo 20 module (`address_ai_extractor`) that integrates Google Gemini AI using the official Google GenAI Python SDK (`google-genai`) to parse unstructured address strings into structured Odoo contact address components.

---

## 1. Features

- **Official Google GenAI Python SDK**: Built using the modern, supported `from google import genai` SDK (`google-genai`).
- **Secure API Key Management**:
  - API keys are configured in **Settings > AI Address Extractor**.
  - Keys are stored securely on the server via `ir.config_parameter`.
  - Restricted to System Administrators (`base.group_system`).
- **Intelligent Address Parsing**:
  - Uses structured JSON output with strict Pydantic schemas.
  - Extracts **Recipient/Company Name**, **Street**, **Street 2**, **City**, **State/Province**, **ZIP/Postal Code**, and **Country**.
  - **No Hallucination**: Explicit system prompt instruction prevents the LLM from fabricating missing information; unavailable fields are strictly left empty.
- **Accurate State & Country Resolution**:
  - Resolves extracted country against existing `res.country` records using ISO codes, aliases (e.g. `USA` → `US`, `UK` → `GB`), and names.
  - Resolves extracted state against `res.country.state` records within the matched country.
- **Dual Contact Workflow**:
  - **Existing Contacts**: Open extractor directly from the contact form header.
  - **New Contacts**: Parse an address and create a new contact in one click.
  - **Overwrite Protection**: Safeguards existing address fields with an optional overwrite checkbox.

---

## 2. Directory Structure

```text
address_ai_extractor/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── gemini_service.py              # Core service handling Google GenAI SDK integration
│   ├── res_config_settings.py         # Gemini API settings
│   └── res_partner.py                 # Res.partner extension with wizard launcher
├── wizard/
│   ├── __init__.py
│   └── address_extraction_wizard.py   # Address extraction transient wizard
├── views/
│   ├── res_config_settings_views.xml  # Settings UI for API key and model
│   ├── address_extraction_wizard_views.xml # Wizard form view
│   ├── res_partner_views.xml          # Partner form view button
│   └── address_menus.xml              # Menus in Contacts app
├── security/
│   └── ir.access.csv                  # Odoo 20 security access rules
├── data/
│   └── ir_config_parameter_data.xml   # Default model configuration parameter
└── README.md
```

---

## 3. Installation & Setup

### Prerequisites

Ensure the official Google GenAI Python SDK is installed in your Odoo Python environment:

```bash
pip install google-genai
```

### Module Installation

1. Add the module directory to your Odoo `addons_path` in `odoo.conf`:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/custom_addons
   ```
2. Update the apps list and install the module via the UI or command line.

---

## 4. Configuration

1. Log into Odoo as an Administrator.
2. Go to **Settings > AI Address Extractor**:
   - **Gemini API Key**: Paste your API key obtained from [Google AI Studio](https://aistudio.google.com/app/apikey).
   - **Gemini Model**: Select your preferred model (e.g. `Gemini 3.5 Flash`).
3. Click **Save**.

---

## 5. Usage Workflows

### Extract & Apply to an Existing Contact
1. Open any contact in **Contacts**.
2. Click the **AI Extract Address** button in the form header.
3. Paste the unformatted address text.
4. Click **Extract Address**.
5. Review the parsed address components and click **Apply to Contact**.

### Extract & Create a New Contact
1. Go to **Contacts > AI Address Extractor** from the top menu.
2. Paste any full address text into the address box.
3. Click **Extract Address**.
4. Review the parsed address components and click **Create New Contact**.
