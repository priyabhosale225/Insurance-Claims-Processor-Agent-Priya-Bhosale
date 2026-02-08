# Autonomous Insurance Claims Processing Agent

> An AI-powered agent that autonomously reads FNOL documents, extracts structured data, validates fields, and routes claims to the correct workflow — with zero human intervention.

---

## Table of Contents

- [Overview](#overview)
- [Approach & Architecture](#approach--architecture)
- [How the Agent Works — Step by Step](#how-the-agent-works--step-by-step)
- [Routing Rules & Priority Logic](#routing-rules--priority-logic)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [How to Run](#how-to-run)
- [How to Test](#how-to-test)
- [5 Sample Scenarios & Expected Results](#5-sample-scenarios--expected-results)
- [JSON Output Format](#json-output-format)
- [Logging System](#logging-system)
- [Fallback Strategy](#fallback-strategy)
- [API Endpoints](#api-endpoints)

---

## Overview

This project is an **Autonomous Insurance Claims Processing Agent** built for the Synapx assessment. The agent takes an FNOL (First Notice of Loss) document as input — either **PDF** or **TXT** format — and autonomously processes it through a 4-step intelligent pipeline:

1. **Extracts** raw text from the document
2. **Identifies** structured fields using AI (OpenAI GPT-4o-mini) or regex fallback
3. **Validates** mandatory fields and detects inconsistencies
4. **Routes** the claim to the appropriate workflow with a clear reasoning

The entire process is automatic. No human input is needed after the document is uploaded. The agent makes the decision and explains why.

---

## Approach & Architecture

### Design Philosophy

The agent is built as a **modular pipeline** — each step is handled by a dedicated Python module. This makes the code clean, testable, and easy to extend. If a new routing rule is needed tomorrow, you only touch `router.py`. If a new extraction method is needed, you only touch `llm_processor.py`. Nothing else changes.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FLASK WEB SERVER                         │
│                    (app.py — port 5000)                     │
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│   │  Upload  │    │  Sample  │    │  History │              │
│   │  API     │    │  API     │    │  API     │              │
│   └────┬─────┘    └────┬─────┘    └──────────┘              │
│        │               │                                    │
│        └───────┬───────┘                                    │
│                ▼                                            │
│   ┌────────────────────────────────────────────────────┐    │
│   │            4-STEP PROCESSING PIPELINE              │    │
│   │                                                    │    │
│   │  ┌──────────────┐   Step 1: Text Extraction        │    │
│   │  │ extractor.py │   PDF → pdfplumber               │    │
│   │  │              │   TXT → file read                │    │
│   │  └──────┬───────┘                                  │    │
│   │         ▼                                          │    │
│   │  ┌──────────────────┐   Step 2: Field Extraction   │    │
│   │  │ llm_processor.py │   Primary: OpenAI GPT-4o-mini│    │
│   │  │                  │   Fallback: Regex patterns   │    │
│   │  └──────┬───────────┘                              │    │
│   │         ▼                                          │    │
│   │  ┌──────────────┐   Step 3: Validation             │    │
│   │  │ validator.py │   Missing fields check           │    │
│   │  │              │   Inconsistency detection        │    │
│   │  └──────┬───────┘                                  │    │
│   │         ▼                                          │    │
│   │  ┌──────────────┐   Step 4: Routing                │    │
│   │  │  router.py   │   5 routes, priority-based       │    │
│   │  │              │   Returns route + reasoning      │    │
│   │  └──────┬───────┘                                  │    │
│   │         ▼                                          │    │
│   │    JSON OUTPUT                                     │    │
│   └────────────────────────────────────────────────────┘    │
│                                                             │
│   ┌────────────────────────────────────────────────────┐    │
│   │              WEB UI (index.html)                   │    │
│   │   Upload area / Sample buttons / Results display   │    │
│   └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## How the Agent Works — Step by Step

### Step 1 — Text Extraction (`agents/extractor.py`)

The agent first reads the uploaded document and extracts all raw text from it.

- **PDF files** → Uses `pdfplumber` library to read every page and extract text. If pdfplumber fails, it falls back to `pypdf` as a secondary extractor.
- **TXT files** → Reads the file content directly (supports UTF-8 and Latin-1 encoding).

The extracted raw text is passed to the next step as a plain string.


### Step 2 — AI Field Extraction (`agents/llm_processor.py`)

This is the brain of the agent. It takes the raw text and extracts **structured fields** from it.

**Primary method — OpenAI GPT-4o-mini:**
When an OpenAI API key is configured, the agent sends the raw text to GPT-4o-mini with a carefully crafted prompt. The AI understands the context of insurance forms and returns a structured JSON with all fields properly mapped — even if the document format varies.

**Fallback method — Regex Pattern Matching:**
When no API key is available (or if the OpenAI call fails), the agent uses regex patterns tuned specifically for the ACORD Automobile Loss Notice form format. These patterns match labels like `POLICY NUMBER`, `DATE OF LOSS`, `ESTIMATED DAMAGE (INR)` and extract their corresponding values from the text.

**Fields extracted (organized into 5 sections):**

| Section                   | Fields                                            |
|---------------------------|---------------------------------------------------|
| **Policy Information**    | Policy Number, Policyholder Name, Effective Dates |
| **Incident Information**  | Date, Time, Location, Description                 |
| **Involved Parties**      | Claimant, Third Parties, Contact Details          |
| **Asset Details**         | Asset Type, Asset ID (VIN), Estimated Damage      |
| **Other Fields**          | Claim Type, Attachments, Initial Estimate         |


### Step 3 — Validation (`agents/validator.py`)

After extraction, the agent validates every field:

**Missing Fields Check:**
Compares extracted fields against a mandatory fields list. Any field that is `null` or empty is flagged as missing. For example, if `effectiveDates` is not found in the document, it appears in the `missingFields` array.


**Inconsistency Detection:**
Checks for logical errors in the data:
- Is the incident date in the future? → Flagged
- Is the estimated damage negative or zero? → Flagged
- Is there a large discrepancy (>50%) between estimated damage and initial estimate? → Flagged
- Is the policy number too short? → Flagged


### Step 4 — Routing (`agents/router.py`)

The agent applies routing rules in **strict priority order** and routes the claim to one of 5 workflows. Once a rule matches, the agent stops and returns that route immediately — it doesn't check lower-priority rules.

The agent also generates a human-readable **reasoning** explaining exactly why it chose that route.

---

## Routing Rules & Priority Logic
Rules are applied top to bottom. The first match wins.

| Priority       | Route                 | Condition                               |  Example                                        |
|----------------|-----------------------|-----------------------------------------|-------------------------------------------------|
| 1 (Highest) 🚨| **Investigation Flag** | Description contains fraud keywords     |"The circumstances appear staged and incosistant |
| 2 🏥          | **Specialist Queue**   | Claim type contains injury keywords     | Claim type = "Injury - Bodily Injury"           |
| 3 📝          | **Manual Review**      | Any mandatory field is missing or empty | effectiveDates is null                          |
| 4 ⚡          | **Fast-track**         | Damage < ₹25,000 AND all fields present | Damage = ₹8,500, all fields complete            |
| 5 (Default) 📦| **Standard Processing**| None of the above conditions match      | Damage = ₹28,500, all fields present            |


**Why this priority order?**
- Fraud detection is always the highest priority — even if fields are missing, a potential fraud must be flagged immediately
- Injury claims need specialist handling (medical/legal expertise) regardless of damage amount
- Missing fields require human intervention before any automated processing
- Low-damage claims with complete data can be fast-tracked safely
- Everything else follows the standard workflow

---

## Project Structure

```
insurance-claims-agent/
│
├── app.py                          # Main Flask application (entry point)
├── config.py                       # Configuration (thresholds, API keys, settings)
├── requirements.txt                # Python dependencies
├── generate_samples.py             # Script to create 5 sample FNOL PDFs
├── .env                            # Environment variables (OpenAI API key)
│
├── agents/                         # Core agent modules (the intelligence)
│   ├── __init__.py
│   ├── extractor.py                # Step 1: PDF/TXT text extraction
│   ├── llm_processor.py            # Step 2: AI field extraction + regex fallback
│   ├── validator.py                # Step 3: Field validation & consistency checks
│   └── router.py                   # Step 4: Claim routing with priority rules
│
├── templates/
│   └── index.html                  # Web UI (single file — HTML + CSS + JS embedded)
│
├── sample_fnol/                    # Pre-generated sample FNOL documents
│   ├── claim_001_fast_track.pdf
│   ├── claim_002_manual_review.pdf
│   ├── claim_003_investigation.pdf
│   ├── claim_004_specialist_injury.pdf
│   └── claim_005_standard.pdf
│
└── uploads/                        # Temporary storage for uploaded files
```

**Note:** The web UI is a **single HTML file** with all CSS and JavaScript embedded — no separate CSS/JS files. Python handles all backend logic.

---

## Tech Stack

| Component         | Technology              | Purpose                                             |
|-------------------|-------------------------|-----------------------------------------------------|
| **Language**      | Python 3.x              | Core application logic                              |
| **Web Framework** | Flask 3.1               | REST API + serves the web UI                        |
| **AI / LLM**      | OpenAI GPT-4o-mini      | Intelligent field extraction from unstructured text |
| **PDF Parsing**   | pdfplumber + pypdf      | Extracts text from PDF documents                    |
| **PDF Creation**  | ReportLab               | Generates sample FNOL form PDFs                     |
| **Environment**   | python-dotenv           | Loads API keys from `.env` file                     |
| **Frontend**      | HTML + CSS + JavaScript | Single-page web interface (embedded in one file)    |
| **Currency**      | ₹ INR (Indian Rupees)   | All monetary values and thresholds                  |

---


## Setup & Installation

### Prerequisites

- **Python 3.8+** installed on your system
- **pip** (Python package manager)
- **OpenAI API Key** (optional — the agent works without it using regex fallback)


### Step-by-step installation

**1. Clone or download the project**

```bash
git clone <your-repo-url>
cd insurance-claims-agent
```

**2. Create a virtual environment**

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```
This installs: Flask, OpenAI SDK, pdfplumber, pypdf, ReportLab, python-dotenv, Werkzeug.


**4. Configure the OpenAI API key**

Open the `.env` file and add your key:

```
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

> **Important:** The agent works perfectly without an API key too — it will automatically use regex-based extraction instead of AI. The AI simply gives better accuracy for varied document formats.
My Recommendation is use Open API Key for testing to get the better accuracy.

**5. Generate sample FNOL documents**

```bash
python generate_samples.py
```

This creates 5 sample PDFs in the `sample_fnol/` folder, each designed to trigger a different routing scenario.

---


## How to Run

After setup, start the agent with one command:

```bash
python app.py
```

You will see this in the terminal:

```
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] ════════════════════════════════════════════════════
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] AUTONOMOUS INSURANCE CLAIMS PROCESSING AGENT
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] ════════════════════════════════════════════════════
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] OpenAI: Configured
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] Formats: PDF, TXT
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] Currency: INR | Fast-track threshold: 25,000
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] ════════════════════════════════════════════════════
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] Waiting for claims...
2026-02-08 11:43:29 | INFO    | claims_agent.server | [Server] Running on http://localhost:5000
```

Now open **http://localhost:5000** in your browser.

---

## How to Test

### Method 1: Web UI — Sample Documents (Quickest)

1. Open http://localhost:5000 in your browser
2. Scroll to **"Quick Test — Sample FNOL Documents"** section
3. Click any of the 5 sample buttons (e.g., "Fast-track Claim")
4. Watch the animated processing steps
5. View the result: route banner, extracted fields, missing fields, and JSON output


### Method 2: Web UI — Upload Your Own Document

1. Click the upload area or drag-and-drop a PDF or TXT file
2. The agent processes it through all 4 steps automatically
3. Results appear on screen with full details


### Method 3: API — Using curl (Command Line)

**Process a sample document:**
```bash
curl -X POST http://localhost:5000/api/process-sample/claim_001_fast_track.pdf
```

**Upload and process a custom file:**
```bash
curl -X POST -F "file=@your_document.pdf" http://localhost:5000/api/process-claim
```

**List all processed claims:**
```bash
curl http://localhost:5000/api/claims
```

**Health check:**
```bash
curl http://localhost:5000/api/health

---

## 5 Sample Scenarios & Expected Results

Each sample PDF is designed to trigger a specific routing path:


### Claim 001 — Fast-track ⚡

| Field               | Value                                        |
|---------------------|----------------------------------------------|
| File                | `claim_001_fast_track.pdf`                   |
| Policyholder        | Rajesh Kumar Sharma                          |
| Location            | MG Road, Bangalore, Karnataka                |
| Damage              | ₹8,500 (below ₹25,000 threshold)             |
| All fields present? | Yes                                          |
| **Expected Route**  | **Fast-track**                               |
| Reason              | Damage below threshold, all fields complete  |


### Claim 002 — Manual Review 📝

| Field              | Value                                         |
|--------------------|-----------------------------------------------|
| File               | `claim_002_manual_review.pdf`                 |
| Policyholder       | Priya Menon                                   |
| Location           | NH-44, Hyderabad, Telangana                   |
| Damage             | ₹1,85,000                                     |
| Missing fields     | effectiveDates (Effective Dates not provided) |
| **Expected Route** | **Manual Review**                             |
| Reason             | Mandatory field missing — needs human review  |


### Claim 003 — Investigation Flag 🚨

| Field                 | Value                                            |
|-----------------------|--------------------------------------------------|
| File                  | `claim_003_investigation.pdf`                    |
| Policyholder          | Suresh Babu Reddy                                |
| Location              | Isolated road near Lonavala, Maharashtra         |
| Damage                | ₹42,00,000 (Total loss — BMW fire)               |
| Fraud keywords found  | "staged", "inconsistent", "fraud" in description |
| **Expected Route**    | **Investigation Flag**                           |
| Reason                | Description contains fraud-related keywords      |


### Claim 004 — Specialist Queue 🏥

| Field               | Value                                                         |
|---------------------|---------------------------------------------------------------|
| File                | `claim_004_specialist_injury.pdf`                             |
| Policyholder        | Anitha Krishnamurthy                                          |
| Location            | Anna Salai, Chennai, Tamil Nadu                               |
| Damage              | ₹3,50,000                                                     |
| Claim type          | Injury - Bodily Injury + Property                             |
| Injuries            | Fractured ribs, head injury, hospitalization                  |
| **Expected Route**  | **Specialist Queue**                                          |
| Reason              | Injury-related claim detected — needs medical/legal expertise |



### Claim 005 — Standard Processing 📦

| Field                 | Value                                                      |
|-----------------------|------------------------------------------------------------|
| File                  | `claim_005_standard.pdf`                                   |
| Policyholder          | Mohammed Irfan Sheikh                                      |
| Location              | Outer Ring Road, Bangalore, Karnataka                      |
| Damage                | ₹28,500 (above ₹25,000 threshold)                          |
| All fields present?   | Yes                                                        |
| **Expected Route**    | **Standard Processing**                                    |
| Reason                | Damage exceeds fast-track threshold, no special conditions |

---

## JSON Output Format

The agent outputs a JSON response matching the assignment specification:

```json
{
  "extractedFields": {
    "policyInformation": {
      "policyNumber": "NIC-MH-2024-08742",
      "policyholderName": "Rajesh Kumar Sharma",
      "effectiveDates": "01/04/2025 to 31/03/2026"
    },
    "incidentInformation": {
      "date": "01/02/2026",
      "time": "10:30 AM",
      "location": "MG Road, Near Forum Mall, Bangalore, Karnataka 560025",
      "description": "Minor rear-end collision at traffic signal..."
    },
    "involvedParties": {
      "claimant": "Rajesh Kumar Sharma",
      "thirdParties": "Vikram Patel",
      "contactDetails": "+91-9876543210"
    },
    "assetDetails": {
      "assetType": "Motor Vehicle - Private Car",
      "assetId": "MA3EYD81S00T52847",
      "estimatedDamage": "8500"
    },
    "otherFields": {
      "claimType": "Auto - Property Damage",
      "attachments": "Photos (3), Police spot report",
      "initialEstimate": "8500"
    }
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage ₹8,500 is below fast-track threshold of ₹25,000. All mandatory fields are present"
}
```

---

## Logging System

The agent uses a structured logging format for clean, professional terminal output:

```
TIMESTAMP | LEVEL | MODULE | [CONTEXT] Message
```

**Example — processing a claim:**

```
2026-02-08 11:28:10 | INFO    | claims_agent.server    | [Upload] Received: 'claim_001_fast_track.pdf' (PDF)
2026-02-08 11:28:10 | INFO    | claims_agent.pipeline  | [CLM-FD35B404] Starting pipeline for: 'claim_001_fast_track.pdf'
2026-02-08 11:28:10 | INFO    | claims_agent.extractor | [CLM-FD35B404] Extracting text from document...
2026-02-08 11:28:10 | INFO    | claims_agent.extractor | [CLM-FD35B404] Extracted 1622 characters successfully
2026-02-08 11:28:10 | INFO    | claims_agent.llm       | [CLM-FD35B404] Sending to OpenAI GPT-4o-mini for field extraction...
2026-02-08 11:28:11 | INFO    | claims_agent.llm       | [CLM-FD35B404] Response: extracted 16 fields via OpenAI GPT-4o-mini
2026-02-08 11:28:11 | INFO    | claims_agent.validator | [CLM-FD35B404] Validating mandatory fields...
2026-02-08 11:28:11 | INFO    | claims_agent.validator | [CLM-FD35B404] All mandatory fields present
2026-02-08 11:28:11 | INFO    | claims_agent.router    | [CLM-FD35B404] Route: Fast-track | Confidence: determined by rules
2026-02-08 11:28:11 | INFO    | claims_agent.router    | [CLM-FD35B404] Reason: Estimated damage ₹8,500 is below fast-track threshold
2026-02-08 11:28:11 | INFO    | claims_agent.pipeline  | [CLM-FD35B404] Pipeline complete -> Fast-track | Missing: 0
```

Each claim gets a unique ID (e.g., `CLM-FD35B404`) so you can trace every step of its processing in the logs.

---

## Fallback Strategy

The agent is designed to **never fail completely**. Here's the fallback chain:

```
OpenAI GPT-4o-mini (Primary)
    │
    ├── ✅ Works → Returns AI-extracted fields
    │
    └── ❌ Fails (network error, quota exceeded, API down)
            │
            └── Regex Pattern Matching (Fallback)
                    │
                    ├── ✅ Works → Returns regex-extracted fields
                    │
                    └── ❌ No patterns match → Returns empty fields
                            │
                            └── Validator catches missing fields
                                    │
                                    └── Routes to "Manual Review"
```

| Scenario                        | What Happens                         | Accuracy                          |
|---------------------------------|--------------------------------------|-----------------------------------|
| OpenAI key set + API works      | Uses GPT-4o-mini                     | Highest (handles varied formats)  |
| OpenAI key set + API fails      | Auto-falls back to regex             | Good (for structured ACORD forms) |
| No OpenAI key at all            | Uses regex directly                  | Good (for structured ACORD forms) |
| Completely unreadable document  | Returns empty fields → Manual Review | Safe (human reviews it)           |

---

## API Endpoints

| Method | Endpoint                         | Description                                   |
|--------|--------------------------------- |-----------------------------------------------|
| `GET`  | `/`                              | Web UI                                        |
| `POST` | `/api/process-claim`             | Upload and process an FNOL document (PDF/TXT) |
| `POST` | `/api/process-sample/<filename>` | Process a pre-generated sample document       |
| `GET`  | `/api/sample-claims`             | List all available sample FNOL files          |
| `GET`  | `/api/claims`                    | Get all processed claims (history)            |
| `GET`  | `/api/health`                    | Server health check                           |

---


### Thank You...
