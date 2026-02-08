"""
Autonomous Insurance Claims Processing Agent
Main Flask Application

Run with: python app.py
Open browser at: http://localhost:5000
"""

import os
import sys
import json
import uuid
import logging
import warnings
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from config import Config
from agents.extractor import DocumentExtractor
from agents.llm_processor import LLMProcessor
from agents.validator import FieldValidator
from agents.router import ClaimRouter
from generate_samples import main as generate_samples


# ── Suppress noisy library logs ──────────────────────────────
warnings.filterwarnings("ignore", message=".*CropBox.*")
warnings.filterwarnings("ignore", message=".*MediaBox.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
logging.getLogger("pdfplumber").setLevel(logging.CRITICAL)

# Suppress default Flask/Werkzeug request logs
werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)


# ── Custom Logger Setup ──────────────────────────────────────

class CleanFormatter(logging.Formatter):
    """Custom formatter: 2026-02-08 11:28:10 | INFO | module | message"""
    def format(self, record):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(5)
        module = record.name.ljust(24)
        return f"{timestamp} | {level} | {module} | {record.getMessage()}"


def setup_logger(name):
    """Create a logger with the clean format."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CleanFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


# Module loggers (matching the reference format)
log_server   = setup_logger("claims_agent.server")
log_pipeline = setup_logger("claims_agent.pipeline")
log_extract  = setup_logger("claims_agent.extractor")
log_llm      = setup_logger("claims_agent.llm")
log_validate = setup_logger("claims_agent.validator")
log_router   = setup_logger("claims_agent.router")


# ── Flask App ─────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize agent components
doc_extractor = DocumentExtractor()
llm_processor = LLMProcessor()
field_validator = FieldValidator()
claim_router = ClaimRouter()

# In-memory store
processed_claims = {}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ── Routes ────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/api/process-claim', methods=['POST'])
def process_claim():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        log_server.warning(f"[Upload] Rejected: {file.filename} (invalid file type)")
        return jsonify({'error': 'Invalid file type. Only PDF and TXT files are allowed.'}), 400

    try:
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        ext = filename.rsplit('.', 1)[1].upper()
        log_server.info(f"[Upload] Received: '{filename}' ({ext})")

        result = _run_pipeline(filepath, filename)

        try:
            os.remove(filepath)
        except OSError:
            pass

        return jsonify(result), 200

    except Exception as e:
        log_pipeline.error(f"[Pipeline] Failed: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/process-sample/<filename>', methods=['POST'])
def process_sample(filename):
    sample_dir = os.path.join(os.path.dirname(__file__), 'sample_fnol')
    filepath = os.path.join(sample_dir, secure_filename(filename))

    if not os.path.exists(filepath):
        log_server.error(f"[Sample] Not found: {filename}")
        return jsonify({'error': 'Sample file not found'}), 404

    try:
        log_server.info(f"[Sample] Processing: '{filename}'")
        result = _run_pipeline(filepath, filename)
        return jsonify(result), 200
    except Exception as e:
        log_pipeline.error(f"[Pipeline] Failed: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/sample-claims', methods=['GET'])
def get_sample_claims():
    sample_dir = os.path.join(os.path.dirname(__file__), 'sample_fnol')
    if not os.path.exists(sample_dir):
        return jsonify([]), 200
    files = [f for f in os.listdir(sample_dir) if f.endswith(('.pdf', '.txt'))]
    return jsonify(sorted(files)), 200


@app.route('/api/claims', methods=['GET'])
def get_claims():
    claims_list = list(processed_claims.values())
    claims_list.sort(key=lambda x: x['processedAt'], reverse=True)
    return jsonify(claims_list), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'openai_configured': bool(app.config.get('OPENAI_API_KEY')),
        'supported_formats': ['PDF', 'TXT']
    }), 200


# ── Pipeline ──────────────────────────────────────────────────

def _run_pipeline(filepath: str, display_name: str) -> dict:
    """Run the complete 4-step claims processing pipeline."""

    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    log_pipeline.info(f"[{claim_id}] Starting pipeline for: '{display_name}'")

    # STEP 1: Extract text
    log_extract.info(f"[{claim_id}] Extracting text from document...")
    raw_text = doc_extractor.extract(filepath)
    if not raw_text or raw_text.strip() == '':
        log_extract.error(f"[{claim_id}] Extraction failed: empty or corrupted file")
        raise ValueError('Could not extract text. File may be empty or corrupted.')
    char_count = len(raw_text)
    log_extract.info(f"[{claim_id}] Extracted {char_count} characters successfully")

    # STEP 2: AI field extraction
    mode = "OpenAI GPT-4o-mini" if Config.OPENAI_API_KEY else "Regex Fallback"
    log_llm.info(f"[{claim_id}] Sending to {mode} for field extraction...")
    extracted_fields = llm_processor.extract_fields(raw_text)
    field_count = sum(1 for sec in extracted_fields.values() for v in sec.values() if v)
    log_llm.info(f"[{claim_id}] Response: extracted {field_count} fields via {mode}")

    # STEP 3: Validation
    log_validate.info(f"[{claim_id}] Validating mandatory fields...")
    missing_fields, inconsistencies = field_validator.validate(extracted_fields)
    if missing_fields:
        names = [f.split('.')[-1] for f in missing_fields]
        log_validate.warning(f"[{claim_id}] Missing {len(missing_fields)} field(s): {', '.join(names)}")
    else:
        log_validate.info(f"[{claim_id}] All mandatory fields present")
    if inconsistencies:
        for issue in inconsistencies:
            log_validate.warning(f"[{claim_id}] Inconsistency: {issue}")

    # STEP 4: Routing
    route, reasoning = claim_router.route(extracted_fields, missing_fields)
    log_router.info(f"[{claim_id}] Route: {route} | Confidence: determined by rules")
    log_router.info(f"[{claim_id}] Reason: {reasoning}")

    # Build result
    result = {
        'claimId': claim_id,
        'filename': display_name,
        'processedAt': datetime.now().isoformat(),
        'extractedFields': extracted_fields,
        'missingFields': missing_fields,
        'inconsistencies': inconsistencies,
        'recommendedRoute': route,
        'reasoning': reasoning,
        'rawTextPreview': raw_text[:500] + ('...' if len(raw_text) > 500 else '')
    }

    processed_claims[claim_id] = result

    log_pipeline.info(f"[{claim_id}] Pipeline complete -> {route} | Missing: {len(missing_fields)} | File: '{display_name}'")
    return result


# ── Start Server ──────────────────────────────────────────────

def get_local_ip():
    """Get the machine's local network IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == '__main__':
    # Suppress Flask's default startup banner ("Serving Flask app", "Debug mode: off")
    import flask.cli
    flask.cli.show_server_banner = lambda *args, **kwargs: None

    api_status = "Configured" if Config.OPENAI_API_KEY else "Not set (regex fallback)"
    local_ip = get_local_ip()

    log_server.info("[Server] ════════════════════════════════════════════════════")
    log_server.info("[Server] AUTONOMOUS INSURANCE CLAIMS PROCESSING AGENT")
    log_server.info("[Server] ════════════════════════════════════════════════════")
    log_server.info(f"[Server] OpenAI: {api_status}")
    log_server.info(f"[Server] Formats: PDF, TXT")
    log_server.info(f"[Server] Currency: INR | Fast-track threshold: 25,000")
    log_server.info("[Server] ════════════════════════════════════════════════════")
    log_server.info(f"[Server] Running on http://localhost:5000")
    
    # Auto-generate sample FNOL documents if not already present
    sample_dir = os.path.join(os.path.dirname(__file__), 'sample_fnol')
    sample_files = [f for f in os.listdir(sample_dir) if f.endswith('.pdf')] if os.path.exists(sample_dir) else []
    if len(sample_files) < 5:
        log_server.info("[Server] Generating sample FNOL documents...")
        try:
            generate_samples()
            log_server.info("[Server] 5 sample FNOL documents generated successfully")
        except Exception as e:
            log_server.warning(f"[Server] Could not generate samples: {e}")
    else:
        log_server.info(f"[Server] {len(sample_files)} sample documents found")

    log_server.info("[Server] Waiting for claims...")
    log_server.info("[Server] ════════════════════════════════════════════════════")
    

    app.run(debug=False, host='0.0.0.0', port=5000)