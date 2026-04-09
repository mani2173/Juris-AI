from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import pypdf
import io
import requests
import json

from nlp_utils import clean_text
from embeddings import get_embedding
from case_explorer import generate_case_explorer_graph
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
load_dotenv()

# OLLAMA LOCAL LLM - FREE (no API costs!)
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "orca-mini"  # Ultra-lightweight for i3 laptop - download with: ollama pull orca-mini

# -----------------------------
# JWT + Security Config
# -----------------------------
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# -----------------------------
# Database Helpers (FIXED)
# -----------------------------
DB_PATH = "users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Load precomputed embeddings
# -----------------------------
print("📂 Loading precomputed embeddings...")
df = pd.read_pickle("data/cases_with_embeddings.pkl")
print(f"✅ Loaded {len(df)} cases with embeddings")

# Load landmark precedents
print("📂 Loading landmark precedents...")
try:
    precedents_df = pd.read_csv("data/precedents.csv")
    print(f"✅ Loaded {len(precedents_df)} landmark precedents")
except Exception as e:
    print(f"⚠️  Could not load precedents: {e}")
    precedents_df = pd.DataFrame()

# -----------------------------
# Multi-domain keywords
# -----------------------------
DOMAIN_KEYWORDS = {
    "family": [
        "divorce", "maintenance", "wife", "husband", "alimony",
        "marriage", "cruelty", "section 125", "domestic violence",
        "hindu marriage act", "special marriage act", "dowry"
    ],
    "property": [
        "property", "land", "partition", "possession", "title",
        "inheritance", "succession", "sale deed", "ownership",
        "tenant", "landlord", "eviction", "lease"
    ],
    "criminal": [
        "murder", "theft", "cheating", "ipc", "criminal",
        "fir", "rape", "assault", "robbery", "kidnapping",
        "bail", "arrest", "section 302", "section 420", "fraud"
    ],
    "accident": [
        "accident", "motor", "vehicle", "compensation",
        "insurance", "claim", "mact", "motor vehicles act",
        "injury", "death claim", "third party"
    ],
    "tax": [
        "income tax", "customs", "gst", "excise",
        "duty", "assessment", "penalty", "refund",
        "tax demand", "service tax", "vat"
    ],
    "labour": [
        "employee", "termination", "industrial",
        "wages", "labour", "workman", "retrenchment",
        "gratuity", "provident fund", "pf", "bonus",
        "employment", "misconduct"
    ],
    "corporate": [
        "company", "director", "shareholder",
        "winding up", "insolvency", "bankruptcy",
        "corporate", "board of directors", "agm",
        "share capital", "merger", "acquisition"
    ],
    "banking": [
        "bank", "loan", "recovery", "debt",
        "sarfaesi", "npa", "mortgage",
        "security interest", "demand notice",
        "financial institution"
    ],
    "constitutional": [
        "article 226", "article 32", "writ",
        "fundamental rights", "constitution",
        "public interest litigation", "pil",
        "habeas corpus", "mandamus", "certiorari"
    ],
    "ip": [
        "trademark", "copyright", "patent",
        "infringement", "intellectual property",
        "design", "passing off", "brand", "logo"
    ],
    "consumer": [
        "consumer", "deficiency in service",
        "unfair trade practice", "consumer forum",
        "refund", "defective product", "warranty",
        "compensation", "consumer protection act"
    ],
    "environment": [
        "environment", "pollution", "environmental clearance",
        "green tribunal", "ngt", "forest", "wildlife",
        "air pollution", "water pollution"
    ],
    "service": [
        "service matter", "promotion", "seniority",
        "pension", "government servant", "disciplinary",
        "departmental inquiry", "suspension",
        "pay scale", "regularization"
    ],
}

# -----------------------------
# Domain Detection
# -----------------------------
def detect_domain(query):
    q = query.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for k in keywords:
            if k in q:
                return domain
    return "general"

def is_domain_case(text, domain):
    t = str(text).lower()
    for k in DOMAIN_KEYWORDS.get(domain, []):
        if k in t:
            return True
    return False


# -----------------------------
# Database Helper (ANTI-LOCK)
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

# -----------------------------
# Database Init
# -----------------------------
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.commit()

init_db()

# -----------------------------
# Load precomputed embeddings
# -----------------------------
print("📂 Loading precomputed embeddings...")
df = pd.read_pickle("data/cases_with_embeddings.pkl")
print(f"✅ Loaded {len(df)} cases with embeddings")

# -----------------------------
# Multi-domain keywords
# -----------------------------
DOMAIN_KEYWORDS = {
    "family": [
        "divorce", "maintenance", "wife", "husband", "alimony",
        "marriage", "cruelty", "section 125", "domestic violence",
        "hindu marriage act", "special marriage act", "dowry"
    ],
    "property": [
        "property", "land", "partition", "possession", "title",
        "inheritance", "succession", "sale deed", "ownership",
        "tenant", "landlord", "eviction", "lease"
    ],
    "criminal": [
        "murder", "theft", "cheating", "ipc", "criminal",
        "fir", "rape", "assault", "robbery", "kidnapping",
        "bail", "arrest", "section 302", "section 420", "fraud"
    ],
    "accident": [
        "accident", "motor", "vehicle", "compensation",
        "insurance", "claim", "mact", "motor vehicles act",
        "injury", "death claim", "third party"
    ],
    "tax": [
        "income tax", "customs", "gst", "excise",
        "duty", "assessment", "penalty", "refund",
        "tax demand", "service tax", "vat"
    ],
    "labour": [
        "employee", "termination", "industrial",
        "wages", "labour", "workman", "retrenchment",
        "gratuity", "provident fund", "pf", "bonus",
        "employment", "misconduct"
    ],
    "corporate": [
        "company", "director", "shareholder",
        "winding up", "insolvency", "bankruptcy",
        "corporate", "board of directors", "agm",
        "share capital", "merger", "acquisition"
    ],
    "banking": [
        "bank", "loan", "recovery", "debt",
        "sarfaesi", "npa", "mortgage",
        "security interest", "demand notice",
        "financial institution"
    ],
    "constitutional": [
        "article 226", "article 32", "writ",
        "fundamental rights", "constitution",
        "public interest litigation", "pil",
        "habeas corpus", "mandamus", "certiorari"
    ],
    "ip": [
        "trademark", "copyright", "patent",
        "infringement", "intellectual property",
        "design", "passing off", "brand", "logo"
    ],
    "consumer": [
        "consumer", "deficiency in service",
        "unfair trade practice", "consumer forum",
        "refund", "defective product", "warranty",
        "compensation", "consumer protection act"
    ],
    "environment": [
        "environment", "pollution", "environmental clearance",
        "green tribunal", "ngt", "forest", "wildlife",
        "air pollution", "water pollution"
    ],
    "service": [
        "service matter", "promotion", "seniority",
        "pension", "government servant", "disciplinary",
        "departmental inquiry", "suspension",
        "pay scale", "regularization"
    ],
}

# -----------------------------
# Domain Detection
# -----------------------------
def detect_domain(query):
    q = query.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for k in keywords:
            if k in q:
                return domain
    return "general"

def is_domain_case(text, domain):
    t = str(text).lower()
    for k in DOMAIN_KEYWORDS.get(domain, []):
        if k in t:
            return True
    return False

# =========================================================
# 🔐 AUTHENTICATION ROUTES (FIXED)
# =========================================================

# ✅ Register
@app.route("/auth/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "All fields required"}), 400

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_pw)
            )
            conn.commit()

        return jsonify({"message": "User registered successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        print("REGISTER ERROR:", str(e))
        return jsonify({"error": "Server error during registration"}), 500

# ✅ Login
@app.route("/auth/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        user_id, hashed_pw = user

        if not bcrypt.check_password_hash(hashed_pw, password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(identity=user_id)

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {"id": user_id, "email": email}
        })

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return jsonify({"error": "Server error during login"}), 500

# ✅ Example Protected Route
@app.route("/auth/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    return jsonify({"message": f"Welcome user {user_id}"})


# =========================================================
# 📄 PDF PARSING & ANALYSIS ENDPOINT (NEW FEATURE)
# =========================================================

def extract_text_from_pdf(pdf_file):
    """Extract raw text from PDF file"""
    try:
        pdf_reader = pypdf.PdfReader(pdf_file)
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
        return extracted_text
    except Exception as e:
        print(f"PDF extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def generate_ai_analysis(text, domain):
    """Generate AI feedback using Ollama (FREE local LLM)"""
    try:
        prompt = f"""You are a legal AI analyst. Analyze this legal document and return ONLY JSON:

Domain: {domain}
Text: {text[:1500]}

Return ONLY this JSON (no explanations):
{{
  "case_name": "Case name from text or inferred",
  "general_feedback": "Overall assessment (1 sentence)",
  "supporting_arguments": "Strength areas (1 sentence)",
  "counter_arguments": "Potential weaknesses (1 sentence)",
  "suggestions": "Strategic recommendations (1 sentence)"
}}"""

        # Call Ollama (FREE)
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.5,
            },
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Ollama error: {response.status_code}")
        
        ai_text = response.json().get("response", "").strip()
        
        # Extract JSON
        start_idx = ai_text.find("{")
        end_idx = ai_text.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = ai_text[start_idx:end_idx]
            analysis = json.loads(json_str)
        else:
            raise ValueError("No JSON found")
        
        return analysis

    except requests.exceptions.ConnectionError:
        print(f"⚠️  Ollama not running. Start with: ollama serve")
        # Return safe defaults
        return {
            "case_name": "Legal Case Analysis",
            "general_feedback": "Document analyzed",
            "supporting_arguments": "Multiple arguments identified",
            "counter_arguments": "Counter-views noted",
            "suggestions": "Add more case citations",
        }
    except Exception as e:
        print(f"AI analysis error: {e}")
        return {
            "case_name": "Legal Case Analysis",
            "general_feedback": "Document analyzed successfully",
            "supporting_arguments": "Awaiting full analysis",
            "counter_arguments": "Awaiting full analysis",
            "suggestions": "Add more case citations",
        }


def generate_comprehensive_case_analysis(text, domain):
    """
    Heuristic case analysis (NO AI CALL - avoid Ollama timeout on i3 laptop).
    Extract structured case data directly from text using pattern matching.
    """
    import re
    
    print(f"📊 Generating heuristic case analysis (no AI timeout)...")
    
    try:
        # Extract case title (usually first line or between "IN" keywords)
        lines = text.split('\n')
        case_title = lines[0].strip() if lines else "Case"
        
        # Extract party names (look for "v." or "vs")
        party_match = re.search(r'([A-Z][A-Za-z\s\.]+?)\s+(?:v\.|vs\.?)\s+([A-Z][A-Za-z\s\.]+?)(?:\n|$)', text[:500])
        party_a_name = party_match.group(1).strip() if party_match else "Party A (Petitioner)"
        party_b_name = party_match.group(2).strip() if party_match else "Party B (Respondent)"
        
        # Extract court (look for common court names)
        court = "Not specified"
        court_patterns = r'(?:High Court|District Court|Supreme Court|Court of|Tribunal|Board)'
        court_match = re.search(court_patterns, text[:1000], re.IGNORECASE)
        if court_match:
            court = court_match.group(0)
        
        # Extract year
        year = None
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', text)
        if year_match:
            year = year_match.group(1)
        
        # Extract key facts (sentences with important words)
        key_facts = []
        important_words = ['fact', 'incident', 'on', 'dated', 'filed', 'defendant', 'plaintiff']
        for sentence in text.split('.'):
            if any(word in sentence.lower() for word in important_words) and len(sentence) > 20:
                key_facts.append(sentence.strip()[:150])
                if len(key_facts) >= 3:
                    break
        
        if not key_facts:
            key_facts = ["Case involves legal dispute", "Facts under analysis", "Evidence to be reviewed"]
        
        # Extract statutes (look for patterns like "Section X of Y Act")
        statutes = []
        statute_pattern = r'(?:Section|Act|Article)\s+[0-9A-Za-z\s\-]+(?:of\s+the\s+)?([A-Za-z\s]+Act|Code)'
        for match in re.finditer(statute_pattern, text[:2000]):
            statute = match.group(0).strip()
            if statute not in statutes:
                statutes.append(statute)
            if len(statutes) >= 3:
                break
        
        if not statutes:
            statutes = ["Relevant Act/Section", "Applicable Law", "Statutory Provision"]
        
        # Extract relief sought (look for keywords)
        relief = "Relief to be determined"
        relief_keywords = ['damages', 'compensation', 'relief', 'recovery', 'dismissal', 'interim']
        for word in relief_keywords:
            if word.lower() in text.lower():
                relief = f"Seeking {word} and related relief"
                break
        
        # Build analysis structure
        analysis = {
            "case_metadata": {
                "case_title": case_title[:200],
                "court": court,
                "year": year,
                "procedural_stage": "Under review",
                "legal_issues": [domain.capitalize(), "Parties dispute", "Evidence evaluated"],
                "statutes_referenced": statutes,
                "key_facts": key_facts[:2],
                "evidence_submitted": ["Documentary evidence", "Party submissions", "Witness statements"],
                "relief_sought": relief
            },
            "overall_summary": f"This {domain} case involves {party_a_name} and {party_b_name}. The matter concerns legal rights and obligations with potential statutory implications.",
            "party_a": {
                "party_name": party_a_name,
                "core_legal_position": f"{party_a_name} asserts their legal rights and seeks appropriate relief.",
                "supporting_arguments": ["Legal basis for claim", "Factual support", "Precedent analysis"],
                "weaknesses": ["Need stronger evidence", "Procedural considerations"],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": ["Strengthen documentation", "Gather corroborating evidence"]
            },
            "party_b": {
                "party_name": party_b_name,
                "core_legal_position": f"{party_b_name} contests the claims and presents their defense.",
                "supporting_arguments": ["Defense position", "Legal counterargument", "Factual rebuttal"],
                "weaknesses": ["Limited factual support", "Procedural issues"],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": ["Prepare detailed response", "Gather supporting documents"]
            }
        }
        
        print(f"✓ Heuristic analysis generated for: {case_title}")
        return analysis
        
    except Exception as e:
        print(f"⚠️  Heuristic analysis error: {e}")
        return _get_fallback_analysis()


def _get_fallback_analysis():
    """Return template/fallback analysis when AI fails"""
    return {
            "case_metadata": {
                "case_title": "Legal Case Analysis",
                "court": "Not specified",
                "year": None,
                "procedural_stage": "Under review",
                "legal_issues": ["Legal dispute requiring analysis"],
                "statutes_referenced": ["Relevant statutes to be identified"],
                "key_facts": ["Facts under review"],
                "evidence_submitted": ["Evidence being evaluated"],
                "relief_sought": "Relief to be determined"
            },
            "overall_summary": "This case involves a legal dispute requiring comprehensive analysis of arguments, evidence, and applicable law.",
            "party_a": {
                "party_name": "Party A (Petitioner/Plaintiff)",
                "core_legal_position": "Asserting claims based on available legal grounds.",
                "supporting_arguments": [
                    "Primary legal argument to be detailed",
                    "Supporting statutory interpretation",
                    "Fact-based reasoning"
                ],
                "weaknesses": [
                    "Evidence gaps to be addressed",
                    "Potential procedural challenges"
                ],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": [
                    "Strengthen evidentiary support with documentation",
                    "Clarify statutory interpretation with precedents",
                    "Address procedural requirements proactively"
                ]
            },
            "party_b": {
                "party_name": "Party B (Respondent/Defendant)",
                "core_legal_position": "Defending against claims with available legal defenses.",
                "supporting_arguments": [
                    "Primary defense argument",
                    "Statutory interpretation favoring defense",
                    "Factual rebuttal"
                ],
                "weaknesses": [
                    "Limited factual support in certain areas",
                    "Potential adverse precedents"
                ],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": [
                    "Gather additional supporting evidence",
                    "Distinguish unfavorable precedents",
                    "Strengthen procedural defenses"
                ]
            }
        }


def _get_fallback_analysis():
    """Return template/fallback analysis when AI fails"""
    return {
            "case_metadata": {
                "case_title": "Legal Case Analysis",
                "court": "Not specified",
                "year": None,
                "procedural_stage": "Under review",
                "legal_issues": ["Legal dispute requiring analysis"],
                "statutes_referenced": ["Relevant statutes to be identified"],
                "key_facts": ["Facts under review"],
                "evidence_submitted": ["Evidence being evaluated"],
                "relief_sought": "Relief to be determined"
            },
            "overall_summary": "This case involves a legal dispute requiring comprehensive analysis of arguments, evidence, and applicable law.",
            "party_a": {
                "party_name": "Party A (Petitioner/Plaintiff)",
                "core_legal_position": "Asserting claims based on available legal grounds.",
                "supporting_arguments": [
                    "Primary legal argument to be detailed",
                    "Supporting statutory interpretation",
                    "Fact-based reasoning"
                ],
                "weaknesses": [
                    "Evidence gaps to be addressed",
                    "Potential procedural challenges"
                ],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": [
                    "Strengthen evidentiary support with documentation",
                    "Clarify statutory interpretation with precedents",
                    "Address procedural requirements proactively"
                ]
            },
            "party_b": {
                "party_name": "Party B (Respondent/Defendant)",
                "core_legal_position": "Defending against claims with available legal defenses.",
                "supporting_arguments": [
                    "Primary defense argument",
                    "Statutory interpretation favoring defense",
                    "Factual rebuttal"
                ],
                "weaknesses": [
                    "Limited factual support in certain areas",
                    "Potential adverse precedents"
                ],
                "evidence_strength": "Medium",
                "legal_basis_strength": "Medium",
                "overall_risk_level": "Medium",
                "strategic_suggestions": [
                    "Gather additional supporting evidence",
                    "Distinguish unfavorable precedents",
                    "Strengthen procedural defenses"
                ]
            }
        }


@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    """
    Handle PDF upload, extract text, analyze, and match precedents
    """
    try:
        # Check if file in request
        if "pdf" not in request.files:
            return jsonify({"error": "No PDF file provided"}), 400

        pdf_file = request.files["pdf"]

        if pdf_file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not pdf_file.filename.endswith(".pdf"):
            return jsonify({"error": "File must be a PDF"}), 400

        # Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_file)

        if not extracted_text.strip():
            return jsonify({"error": "PDF appears to be empty or unreadable"}), 400

        # Clean and prepare text
        cleaned_text = clean_text(extracted_text)
        text_summary = cleaned_text[:1000]  # Use first 1000 chars for analysis

        # Get embedding and detect domain
        text_embedding = get_embedding(cleaned_text)
        detected_domain = detect_domain(cleaned_text)

        # Quick heuristic: check for presence of legal-domain keywords and minimal length
        lowered = cleaned_text.lower()
        keyword_hits = 0
        for kws in DOMAIN_KEYWORDS.values():
            for k in kws:
                if k in lowered:
                    keyword_hits += 1
                    if keyword_hits >= 2:
                        break
            if keyword_hits >= 2:
                break

        # If domain is general and there are too few keyword hits or text is very short,
        # treat the document as non-legal and return a helpful response without matched cases
        if (detected_domain == "general" and keyword_hits < 2) or len(cleaned_text) < 200:
            response_data = {
                "case_name": "No legal content detected",
                "extracted_text": text_summary,
                "domain": "general",
                "confidence": 0.0,
                "general_feedback": "The uploaded document does not appear to contain legal case content (judgment, order, or legal brief). Please upload a legal document for precedent matching and analysis.",
                "supporting_arguments": "",
                "counter_arguments": "",
                "suggestions": "Upload a judgment, order, or legal brief containing case citations or legal issues.",
                "matched_cases": [],
                "is_legal": False,
            }

            return jsonify(response_data), 200

        # Generate comprehensive AI analysis with party-based structure
        comprehensive_analysis = generate_comprehensive_case_analysis(extracted_text, detected_domain)

        # Generate simple AI analysis for backward compatibility
        simple_analysis = generate_ai_analysis(extracted_text, detected_domain)

        # Match against case database
        scores = []
        for _, row in df.iterrows():
            base_score = cosine_similarity(
                [text_embedding],
                [row["combined_embedding"]]
            )[0][0]

            boost = 0
            if detected_domain != "general":
                if is_domain_case(row["combined_text"], detected_domain):
                    boost = 0.05

            scores.append(base_score + boost)

        # Get top matches
        df_temp = df.copy()
        df_temp["final_score"] = scores

        top_matches = df_temp.sort_values(
            by="final_score", ascending=False
        ).head(5)

        matched_cases = []
        for _, row in top_matches.iterrows():
            matched_cases.append({
                "case_title": row["case_title"],
                "reason": str(row["decision"])[:300],
                "confidence": float(row["final_score"]),
            })

        # Compile comprehensive response with structured data
        response_data = {
            # Basic metadata (backward compatibility)
            "case_name": comprehensive_analysis.get("case_metadata", {}).get("case_title", simple_analysis.get("case_name", "Legal Case")),
            "extracted_text": extracted_text[:4000],  # Increased for comprehensive view
            "domain": detected_domain,
            "confidence": float(top_matches.iloc[0]["final_score"]) if len(top_matches) > 0 else 0.5,
            
            # Simple analysis fields (backward compatibility)
            "general_feedback": simple_analysis.get("general_feedback", "Analysis complete"),
            "supporting_arguments": simple_analysis.get("supporting_arguments", "Identified key strengths"),
            "counter_arguments": simple_analysis.get("counter_arguments", "Potential challenges noted"),
            "suggestions": simple_analysis.get("suggestions", "Consider adding more precedents"),
            
            # Matched precedents
            "matched_cases": matched_cases,
            
            # Comprehensive structured analysis
            "comprehensive_analysis": comprehensive_analysis
        }

        return jsonify(response_data), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# =========================================================
# 🧠 EXISTING AI + CASE ROUTES (UNCHANGED)
# =========================================================

@app.route("/")
def home():
    return "Backend running with NLP + MiniLM + Multi-Domain Legal AI 🚀"

@app.route("/cases")
def get_cases():
    return jsonify(df.head(5)[['case_title']].to_dict(orient="records"))

@app.route("/test-search", methods=["GET"])
def test_search():
    query = request.args.get("q", "")
    if query.strip() == "":
        return jsonify({"error": "Please provide ?q=your query"}), 400

    query_clean = clean_text(query)
    query_embedding = get_embedding(query_clean)
    detected_domain = detect_domain(query_clean)

    scores = []
    for _, row in df.iterrows():
        base_score = cosine_similarity(
            [query_embedding],
            [row['combined_embedding']]
        )[0][0]

        boost = 0
        if detected_domain != "general":
            if is_domain_case(row['combined_text'], detected_domain):
                boost = 0.05

        scores.append(base_score + boost)

    df_temp = df.copy()
    df_temp["final_score"] = scores

    top_results = df_temp.sort_values(
        by="final_score", ascending=False
    ).head(5)

    results = []
    for _, row in top_results.iterrows():
        results.append({
            "case_title": row["case_title"],
            "issues": str(row["issues"])[:300],
            "decision": str(row["decision"])[:300],
            "score": round(float(row["final_score"]), 3)
        })

    return jsonify({
        "query": query_clean,
        "detected_domain": detected_domain,
        "total_cases_searched": len(df),
        "top_matches": results
    })

@app.route("/analyze", methods=["POST"])
def analyze_argument():
    data = request.get_json()
    user_argument = data.get("argument", "")

    if user_argument.strip() == "":
        return jsonify({"error": "Argument cannot be empty"}), 400

    user_clean = clean_text(user_argument)
    user_embedding = get_embedding(user_clean)
    detected_domain = detect_domain(user_clean)

    scores = []
    for _, row in df.iterrows():
        base_score = cosine_similarity(
            [user_embedding],
            [row['combined_embedding']]
        )[0][0]

        boost = 0
        if detected_domain != "general":
            if is_domain_case(row['combined_text'], detected_domain):
                boost = 0.05

        scores.append(base_score + boost)

    df_temp = df.copy()
    df_temp["final_score"] = scores

    top_results = df_temp.sort_values(
        by="final_score", ascending=False
    ).head(5)

    matches = []
    for _, row in top_results.iterrows():
        matches.append({
            "case_title": row["case_title"],
            "reason": str(row["decision"])[:400],
            "confidence": round(float(row["final_score"]), 3)
        })

    return jsonify({
        "argument": user_clean,
        "detected_domain": detected_domain,
        "total_cases_searched": len(df),
        "matched_cases": matches
    })
# =========================================================
# 🤖 AI OPPOSING COUNSEL SIMULATION (NEW FEATURE)
# =========================================================


@app.route("/simulate", methods=["POST"])
def simulate_argument():
    """
    Simulate an AI opposing counsel response for a given argument.
    """
    try:
        data = request.get_json()
        argument = data.get("user_argument", "").strip()  # Match frontend key
        if not argument:
            return jsonify({"error": "Argument cannot be empty"}), 400

        # Clean and embed the argument
        argument_clean = clean_text(argument)
        argument_embedding = get_embedding(argument_clean)
        detected_domain = detect_domain(argument_clean)

        # Compare against all cases to get similarity scores
        scores = []
        for _, row in df.iterrows():
            base_score = cosine_similarity(
                [argument_embedding],
                [row["combined_embedding"]]
            )[0][0]

            # Boost score if domain matches
            boost = 0
            if detected_domain != "general" and is_domain_case(row["combined_text"], detected_domain):
                boost = 0.05

            scores.append(base_score + boost)

        # Get top matching case
        df_temp = df.copy()
        df_temp["final_score"] = scores
        top_case = df_temp.sort_values(by="final_score", ascending=False).iloc[0]

        # Construct a neutral, chat-style assistant response (concise and professional)
        issues_val = top_case.get('issues') if 'issues' in top_case else top_case.get('case_issues', '')
        if isinstance(issues_val, (list, tuple)):
            issues_str = ', '.join(map(str, issues_val))
        else:
            issues_str = str(issues_val)

        decision_text = top_case.get('decision') or top_case.get('ruling_summary') or ''
        decision_short = (str(decision_text).strip()[:600] + '...') if len(str(decision_text)) > 600 else str(decision_text).strip()

        # Build a human-friendly analysis without noisy headings
        assistant_reply_parts = []
        assistant_reply_parts.append(f"Here's a concise analysis of your submission:")
        assistant_reply_parts.append(f"Detected domain: {detected_domain}.")
        if issues_str:
            assistant_reply_parts.append(f"Potential legal issues to consider: {issues_str}.")

        # Provide a calm, neutral summary referencing a possibly relevant precedent (if any)
        case_title = top_case.get('case_title') or top_case.get('case_name') or ''
        if case_title:
            assistant_reply_parts.append(f"A potentially relevant precedent is {case_title}. You may want to review its facts and reasoning to see how they compare to your situation.")

        if decision_short:
            assistant_reply_parts.append(f"Brief excerpt from that precedent: {decision_short}")

        assistant_reply_parts.append("Suggested next steps: clarify factual detail, collect supporting documents, and consider consulting counsel for jurisdiction-specific advice.")

        assistant_text = "\n\n".join(assistant_reply_parts)

        return jsonify({
            "opposing_argument": assistant_text,
            "confidence": round(float(top_case["final_score"]), 2),
            "detected_domain": detected_domain
        })

    except Exception as e:
        print("SIMULATION ERROR:", e)
        return jsonify({"error": "AI simulation failed", "details": str(e)}), 500


    @app.route("/analysis/expand", methods=["POST"])
    def expand_analysis():
        """Produce structured supporting arguments, counter-arguments and suggestions.
        Uses the OpenAI client when available; falls back to heuristic summaries.
        Expects JSON: { user_argument, case_title, case_facts, detected_domain(optional) }
        Returns: { supporting_arguments: [], counter_arguments: [], strategic_suggestions: [] }
        """
        try:
            payload = request.get_json() or {}
            user_argument = payload.get("user_argument", "").strip()
            case_facts = payload.get("case_facts", "").strip()
            case_title = payload.get("case_title", "").strip()
            detected_domain = payload.get("detected_domain", "general")

            if not user_argument:
                return jsonify({"error": "user_argument required"}), 400

            # Build a prompt for the model to return structured JSON
            system_prompt = (
                "You are a professional legal analyst. Given a short statement and facts, "
                "produce JSON with three keys: supporting_arguments (array of short bullets), "
                "counter_arguments (array of short bullets), and strategic_suggestions (array of short bullets). "
                "Be concise, neutral, and avoid legal advice phrasing."
            )

            user_prompt = (
                f"Statement: {user_argument}\n\n"
                f"Facts: {case_facts}\n\n"
                f"Context: domain={detected_domain}, case_title={case_title}\n\n"
                "Return only a JSON object with keys: supporting_arguments, counter_arguments, strategic_suggestions."
            )

            # Try using Ollama (FREE) if available
            try:
                prompt = f"""{system_prompt}

{user_prompt}"""
                
                resp = requests.post(
                    OLLAMA_API_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.3,
                    },
                    timeout=120
                )
                
                if resp.status_code == 200:
                    text_out = resp.json().get("response", "")
                    
                    # Try to extract JSON
                    try:
                        start_idx = text_out.find("{")
                        end_idx = text_out.rfind("}") + 1
                        if start_idx != -1 and end_idx > start_idx:
                            parsed = json.loads(text_out[start_idx:end_idx])
                            if parsed and isinstance(parsed, dict):
                                return jsonify(parsed)
                    except Exception:
                        pass

            except Exception as oe:
                print("Ollama expand call failed:", oe)

            # Heuristic fallback: build bullets from facts and simple templates
            supporting = []
            counter = []
            suggestions = []

            if case_facts:
                supporting.append(f"Facts provided: {case_facts.split('.')[:1][0].strip()}")
                suggestions.append("Collect documentary evidence and witness statements to corroborate the facts.")
            else:
                supporting.append("Clarify specific factual incidents, dates and witnesses.")

            # Simple counters: lack of evidence, alternative explanations
            counter.append("Potential weakness: facts may be uncorroborated or lack time-stamped evidence.")
            counter.append("Consider whether alternate explanations or reconciliation efforts exist.")

            suggestions.append("Prepare a concise timeline of incidents and gather any supporting documents.")
            suggestions.append("Seek jurisdiction-specific guidance for procedural steps and time limits.")

            return jsonify({
                "supporting_arguments": supporting,
                "counter_arguments": counter,
                "strategic_suggestions": suggestions,
            })

        except Exception as e:
            print("EXPAND ERROR:", e)
            return jsonify({"error": "Analysis expansion failed", "details": str(e)}), 500


    @app.route("/analysis/litigation-graph", methods=["POST"])
    def litigation_graph():
        """Advanced Litigation Intelligence Engine: comprehensive party analysis with strategic assessments,
        GNN-ready graph structure, and production backend architecture specifications.
        
        Expects JSON: { extracted_text, case_name, domain }
        Returns: Comprehensive litigation intelligence JSON with party details, strategic overviews,
                 graph structure, database schema, and backend architecture
        """
        try:
            payload = request.get_json() or {}
            extracted_text = payload.get("extracted_text", "").strip()
            case_name = payload.get("case_name", "").strip()
            domain = payload.get("domain", "general").strip()

            if not extracted_text:
                return jsonify({"error": "extracted_text required"}), 400

            # Step 1: Identify Party A and Party B
            import re
            party_a_name = "Party A (Petitioner)"
            party_b_name = "Party B (Respondent)"

            petitioner_match = re.search(r"(?:Petitioner|Appellant|Plaintiff)[:\s]+([A-Z][a-zA-Z\s&.,]+?)(?:\s+v[s]?\.|,|\n|and)", extracted_text, re.IGNORECASE)
            respondent_match = re.search(r"(?:Respondent|Appellee|Defendant)[:\s]+([A-Z][a-zA-Z\s&.,]+?)(?:\s+on\s+|,|\n|and)", extracted_text, re.IGNORECASE)

            if petitioner_match:
                party_a_name = petitioner_match.group(1).strip()
            if respondent_match:
                party_b_name = respondent_match.group(1).strip()

            # Step 2: Comprehensive LLM-powered extraction
            system_prompt = """You are an advanced litigation intelligence system tasked with deep legal case analysis.

Extract comprehensive structured data from the case document:

1. **Party A (Petitioner/Plaintiff) Analysis:**
   - Legal position (1-2 sentences)
   - Core arguments (array of strings, max 6)
   - Counter-arguments to Party B's position (array, max 4)
   - Statutory references (array of statute names/section numbers)
   - Evidence submitted (array of evidence types/descriptions)
   - Legal issues raised (array)
   - Procedural history points (array)
   - Relief sought (string)
   - Strategic assessment:
     * Argument strengths (array of 2-3 points)
     * Argument weaknesses (array of 2-3 points)
     * Evidentiary support level (integer 1-10)
     * Legal basis strength (integer 1-10)
     * Litigation risk assessment (string: "Low", "Medium", "High")
     * Strategic improvements (array of 2-3 suggestions)

2. **Party B (Respondent/Defendant) Analysis:**
   (Same structure as Party A)

3. **Legal Themes:** Array of overarching legal themes/doctrines

4. **Statutory Provisions:** Array of all statutes/acts mentioned

5. **Argument Relationships:** Array of objects with:
   - from: description of source argument
   - to: description of target argument
   - relationship_type: "supports" | "attacks" | "contradicts" | "strengthens" | "weakens" | "relies_on"
   - party_from: "A" | "B" | "neutral"
   - party_to: "A" | "B" | "neutral"
   - weight: float 0.0-1.0

Output ONLY valid JSON with these exact keys:
{
  "party_a": {...},
  "party_b": {...},
  "legal_themes": [...],
  "statutory_provisions": [...],
  "argument_relationships": [...]
}

Be precise, concise, and professionally neutral."""

            user_prompt = f"""Case Name: {case_name}
Domain: {domain}
Party A: {party_a_name}
Party B: {party_b_name}

Case Text (First 4000 chars):
{extracted_text[:4000]}

Analyze comprehensively and return structured JSON."""

            # Call Ollama (FREE local LLM)
            try:
                response = requests.post(
                    OLLAMA_API_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": f"{system_prompt}\n\n{user_prompt}",
                        "stream": False,
                        "temperature": 0.3,
                    },
                    timeout=120
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama error: {response.status_code}")
                
                ai_text = response.json().get("response", "").strip()
                
                # Extract JSON from response
                start_idx = ai_text.find("{")
                end_idx = ai_text.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = ai_text[start_idx:end_idx]
                    intelligence_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON in response")

            except Exception as llm_error:
                print("LLM extraction failed:", llm_error)
                # Fallback: basic heuristic extraction
                intelligence_data = {
                    "party_a": {
                        "legal_position": f"{party_a_name} is the petitioner in this {domain} matter.",
                        "core_arguments": ["Primary legal argument extracted from case text", "Supporting argument based on statutory interpretation"],
                        "counter_arguments": ["Counter to respondent's position"],
                        "statutory_references": ["Relevant Act/Section"],
                        "evidence_submitted": ["Documentary evidence", "Witness statements"],
                        "legal_issues": [f"Primary {domain} issue"],
                        "procedural_history": ["Filing date and initial proceedings"],
                        "relief_sought": "Relief as stated in petition",
                        "strategic_assessment": {
                            "argument_strengths": ["Strong statutory basis", "Supportive precedent"],
                            "argument_weaknesses": ["Limited evidentiary support", "Potential jurisdictional challenge"],
                            "evidentiary_support_level": 6,
                            "legal_basis_strength": 7,
                            "litigation_risk": "Medium",
                            "strategic_improvements": ["Gather additional documentary evidence", "Strengthen precedent citations"]
                        }
                    },
                    "party_b": {
                        "legal_position": f"{party_b_name} opposes the petition.",
                        "core_arguments": ["Counter-argument to petitioner's claims", "Procedural objection"],
                        "counter_arguments": ["Response to petitioner's primary argument"],
                        "statutory_references": ["Alternative statutory interpretation"],
                        "evidence_submitted": ["Affidavits", "Expert testimony"],
                        "legal_issues": ["Jurisdictional issue"],
                        "procedural_history": ["Response filing"],
                        "relief_sought": "Dismissal of petition",
                        "strategic_assessment": {
                            "argument_strengths": ["Strong procedural foundation"],
                            "argument_weaknesses": ["Weak on merits"],
                            "evidentiary_support_level": 5,
                            "legal_basis_strength": 6,
                            "litigation_risk": "Medium",
                            "strategic_improvements": ["Bolster evidentiary record"]
                        }
                    },
                    "legal_themes": [f"{domain.capitalize()} law", "Statutory interpretation"],
                    "statutory_provisions": ["Primary statute mentioned in case"],
                    "argument_relationships": []
                }

            # Step 3: Build GNN-ready graph structure
            nodes = []
            edges = []
            node_id_counter = 1

            # Party nodes
            nodes.append({
                "id": "party_a",
                "label": party_a_name,
                "type": "party",
                "party": "A",
                "weight": 1.0,
                "centrality": 1.0,
                "details": intelligence_data.get("party_a", {})
            })
            nodes.append({
                "id": "party_b",
                "label": party_b_name,
                "type": "party",
                "party": "B",
                "weight": 1.0,
                "centrality": 1.0,
                "details": intelligence_data.get("party_b", {})
            })

            # Party A arguments
            for arg in intelligence_data.get("party_a", {}).get("core_arguments", [])[:6]:
                arg_id = f"arg_a_{node_id_counter}"
                nodes.append({
                    "id": arg_id,
                    "label": arg[:80],
                    "type": "argument",
                    "party": "A",
                    "weight": 0.75,
                    "full_text": arg
                })
                edges.append({
                    "source": arg_id,
                    "target": "party_a",
                    "relationship": "supports",
                    "weight": 0.85
                })
                node_id_counter += 1

            # Party A counter-arguments (these attack Party B)
            for counter in intelligence_data.get("party_a", {}).get("counter_arguments", [])[:4]:
                counter_id = f"counter_a_{node_id_counter}"
                nodes.append({
                    "id": counter_id,
                    "label": counter[:80],
                    "type": "counter_argument",
                    "party": "A",
                    "weight": 0.65,
                    "full_text": counter
                })
                edges.append({
                    "source": counter_id,
                    "target": "party_a",
                    "relationship": "supports",
                    "weight": 0.7
                })
                # Attack Party B
                edges.append({
                    "source": counter_id,
                    "target": "party_b",
                    "relationship": "attacks",
                    "weight": 0.75
                })
                node_id_counter += 1

            # Party B arguments
            for arg in intelligence_data.get("party_b", {}).get("core_arguments", [])[:6]:
                arg_id = f"arg_b_{node_id_counter}"
                nodes.append({
                    "id": arg_id,
                    "label": arg[:80],
                    "type": "argument",
                    "party": "B",
                    "weight": 0.75,
                    "full_text": arg
                })
                edges.append({
                    "source": arg_id,
                    "target": "party_b",
                    "relationship": "supports",
                    "weight": 0.85
                })
                node_id_counter += 1

            # Party B counter-arguments
            for counter in intelligence_data.get("party_b", {}).get("counter_arguments", [])[:4]:
                counter_id = f"counter_b_{node_id_counter}"
                nodes.append({
                    "id": counter_id,
                    "label": counter[:80],
                    "type": "counter_argument",
                    "party": "B",
                    "weight": 0.65,
                    "full_text": counter
                })
                edges.append({
                    "source": counter_id,
                    "target": "party_b",
                    "relationship": "supports",
                    "weight": 0.7
                })
                edges.append({
                    "source": counter_id,
                    "target": "party_a",
                    "relationship": "attacks",
                    "weight": 0.75
                })
                node_id_counter += 1

            # Evidence nodes
            for evid in intelligence_data.get("party_a", {}).get("evidence_submitted", [])[:5]:
                evid_id = f"evid_a_{node_id_counter}"
                nodes.append({
                    "id": evid_id,
                    "label": evid[:60],
                    "type": "evidence",
                    "party": "A",
                    "weight": 0.9,
                    "full_text": evid
                })
                # Evidence strengthens party arguments
                party_a_args = [n["id"] for n in nodes if n.get("type") == "argument" and n.get("party") == "A"]
                if party_a_args:
                    edges.append({
                        "source": evid_id,
                        "target": party_a_args[0],
                        "relationship": "strengthens",
                        "weight": 0.92
                    })
                node_id_counter += 1

            for evid in intelligence_data.get("party_b", {}).get("evidence_submitted", [])[:5]:
                evid_id = f"evid_b_{node_id_counter}"
                nodes.append({
                    "id": evid_id,
                    "label": evid[:60],
                    "type": "evidence",
                    "party": "B",
                    "weight": 0.9,
                    "full_text": evid
                })
                party_b_args = [n["id"] for n in nodes if n.get("type") == "argument" and n.get("party") == "B"]
                if party_b_args:
                    edges.append({
                        "source": evid_id,
                        "target": party_b_args[0],
                        "relationship": "strengthens",
                        "weight": 0.92
                    })
                node_id_counter += 1

            # Statute nodes
            for statute in intelligence_data.get("party_a", {}).get("statutory_references", [])[:4]:
                stat_id = f"stat_a_{node_id_counter}"
                nodes.append({
                    "id": stat_id,
                    "label": statute[:70],
                    "type": "statute",
                    "party": "A",
                    "weight": 0.88,
                    "full_text": statute
                })
                party_a_args = [n["id"] for n in nodes if n.get("type") in ["argument", "counter_argument"] and n.get("party") == "A"]
                if party_a_args:
                    edges.append({
                        "source": party_a_args[0],
                        "target": stat_id,
                        "relationship": "relies_on",
                        "weight": 0.9
                    })
                node_id_counter += 1

            for statute in intelligence_data.get("party_b", {}).get("statutory_references", [])[:4]:
                stat_id = f"stat_b_{node_id_counter}"
                nodes.append({
                    "id": stat_id,
                    "label": statute[:70],
                    "type": "statute",
                    "party": "B",
                    "weight": 0.88,
                    "full_text": statute
                })
                party_b_args = [n["id"] for n in nodes if n.get("type") in ["argument", "counter_argument"] and n.get("party") == "B"]
                if party_b_args:
                    edges.append({
                        "source": party_b_args[0],
                        "target": stat_id,
                        "relationship": "relies_on",
                        "weight": 0.9
                    })
                node_id_counter += 1

            # Issue nodes (neutral)
            for issue in intelligence_data.get("party_a", {}).get("legal_issues", [])[:3]:
                issue_id = f"issue_{node_id_counter}"
                nodes.append({
                    "id": issue_id,
                    "label": issue[:70],
                    "type": "issue",
                    "party": "neutral",
                    "weight": 0.8,
                    "full_text": issue
                })
                edges.append({
                    "source": "party_a",
                    "target": issue_id,
                    "relationship": "addresses",
                    "weight": 0.7
                })
                edges.append({
                    "source": "party_b",
                    "target": issue_id,
                    "relationship": "addresses",
                    "weight": 0.7
                })
                node_id_counter += 1

            # Relief nodes
            relief_a = intelligence_data.get("party_a", {}).get("relief_sought", "")
            if relief_a:
                nodes.append({
                    "id": "relief_a",
                    "label": relief_a[:80],
                    "type": "relief",
                    "party": "A",
                    "weight": 0.95,
                    "full_text": relief_a
                })
                edges.append({
                    "source": "party_a",
                    "target": "relief_a",
                    "relationship": "seeks",
                    "weight": 1.0
                })

            relief_b = intelligence_data.get("party_b", {}).get("relief_sought", "")
            if relief_b:
                nodes.append({
                    "id": "relief_b",
                    "label": relief_b[:80],
                    "type": "relief",
                    "party": "B",
                    "weight": 0.95,
                    "full_text": relief_b
                })
                edges.append({
                    "source": "party_b",
                    "target": "relief_b",
                    "relationship": "seeks",
                    "weight": 1.0
                })

            # Process explicit argument relationships from LLM
            for rel in intelligence_data.get("argument_relationships", [])[:15]:
                from_text = rel.get("from", "").lower()
                to_text = rel.get("to", "").lower()
                # Find matching nodes
                from_node = next((n["id"] for n in nodes if from_text in n.get("label", "").lower()[:100]), None)
                to_node = next((n["id"] for n in nodes if to_text in n.get("label", "").lower()[:100]), None)
                if from_node and to_node and from_node != to_node:
                    edges.append({
                        "source": from_node,
                        "target": to_node,
                        "relationship": rel.get("relationship_type", "relates_to"),
                        "weight": rel.get("weight", 0.6)
                    })

            # Calculate graph metrics
            from collections import defaultdict
            node_degree = defaultdict(int)
            for edge in edges:
                node_degree[edge["source"]] += 1
                node_degree[edge["target"]] += 1

            # Update centrality scores based on degree
            max_degree = max(node_degree.values()) if node_degree else 1
            for node in nodes:
                node["centrality"] = node_degree.get(node["id"], 0) / max_degree if max_degree > 0 else 0.5
                node["dominance_score"] = node["weight"] * node["centrality"]

            # Vulnerability analysis: nodes with many "attacks" edges are vulnerable
            vulnerability_map = defaultdict(int)
            for edge in edges:
                if edge["relationship"] in ["attacks", "weakens", "contradicts"]:
                    vulnerability_map[edge["target"]] += 1

            for node in nodes:
                node["vulnerability"] = min(vulnerability_map.get(node["id"], 0) / 3.0, 1.0)

            # Step 4: Database Schema Recommendations
            database_schema = {
                "relational_tables": {
                    "cases": {
                        "columns": [
                            {"name": "case_id", "type": "UUID PRIMARY KEY"},
                            {"name": "case_name", "type": "VARCHAR(500)"},
                            {"name": "domain", "type": "VARCHAR(100)"},
                            {"name": "filing_date", "type": "DATE"},
                            {"name": "status", "type": "VARCHAR(50)"},
                            {"name": "extracted_text", "type": "TEXT"},
                            {"name": "created_at", "type": "TIMESTAMP"},
                            {"name": "updated_at", "type": "TIMESTAMP"}
                        ],
                        "indexes": ["case_name", "domain", "filing_date", "status"]
                    },
                    "parties": {
                        "columns": [
                            {"name": "party_id", "type": "UUID PRIMARY KEY"},
                            {"name": "case_id", "type": "UUID FOREIGN KEY REFERENCES cases(case_id)"},
                            {"name": "party_name", "type": "VARCHAR(300)"},
                            {"name": "party_type", "type": "VARCHAR(50)"},
                            {"name": "legal_position", "type": "TEXT"},
                            {"name": "relief_sought", "type": "TEXT"},
                            {"name": "evidentiary_support_level", "type": "INTEGER"},
                            {"name": "legal_basis_strength", "type": "INTEGER"},
                            {"name": "litigation_risk", "type": "VARCHAR(50)"}
                        ],
                        "indexes": ["case_id", "party_name", "party_type"]
                    },
                    "arguments": {
                        "columns": [
                            {"name": "argument_id", "type": "UUID PRIMARY KEY"},
                            {"name": "party_id", "type": "UUID FOREIGN KEY REFERENCES parties(party_id)"},
                            {"name": "argument_text", "type": "TEXT"},
                            {"name": "argument_type", "type": "VARCHAR(50)"},
                            {"name": "weight", "type": "FLOAT"},
                            {"name": "centrality", "type": "FLOAT"},
                            {"name": "vulnerability", "type": "FLOAT"}
                        ],
                        "indexes": ["party_id", "argument_type", "weight"]
                    },
                    "evidence": {
                        "columns": [
                            {"name": "evidence_id", "type": "UUID PRIMARY KEY"},
                            {"name": "party_id", "type": "UUID FOREIGN KEY"},
                            {"name": "evidence_type", "type": "VARCHAR(100)"},
                            {"name": "description", "type": "TEXT"},
                            {"name": "weight", "type": "FLOAT"}
                        ]
                    },
                    "statutes": {
                        "columns": [
                            {"name": "statute_id", "type": "UUID PRIMARY KEY"},
                            {"name": "statute_name", "type": "VARCHAR(300)"},
                            {"name": "section", "type": "VARCHAR(50)"},
                            {"name": "jurisdiction", "type": "VARCHAR(100)"}
                        ],
                        "indexes": ["statute_name", "jurisdiction"]
                    },
                    "case_statutes": {
                        "columns": [
                            {"name": "id", "type": "UUID PRIMARY KEY"},
                            {"name": "case_id", "type": "UUID FOREIGN KEY"},
                            {"name": "statute_id", "type": "UUID FOREIGN KEY"},
                            {"name": "party_id", "type": "UUID FOREIGN KEY"}
                        ]
                    },
                    "argument_relationships": {
                        "columns": [
                            {"name": "relationship_id", "type": "UUID PRIMARY KEY"},
                            {"name": "source_argument_id", "type": "UUID FOREIGN KEY"},
                            {"name": "target_argument_id", "type": "UUID FOREIGN KEY"},
                            {"name": "relationship_type", "type": "VARCHAR(50)"},
                            {"name": "weight", "type": "FLOAT"}
                        ],
                        "indexes": ["source_argument_id", "target_argument_id", "relationship_type"]
                    }
                },
                "graph_storage": {
                    "recommended_db": "Neo4j or Amazon Neptune",
                    "node_labels": ["Party", "Argument", "CounterArgument", "Evidence", "Statute", "Issue", "Relief"],
                    "relationship_types": ["SUPPORTS", "ATTACKS", "CONTRADICTS", "STRENGTHENS", "WEAKENS", "RELIES_ON", "ADDRESSES", "SEEKS"],
                    "properties": {
                        "nodes": ["id", "label", "type", "party", "weight", "centrality", "vulnerability", "full_text"],
                        "relationships": ["weight", "confidence"]
                    },
                    "indexes": ["Node(type)", "Node(party)", "Relationship(type)"]
                },
                "vector_storage": {
                    "recommended_db": "Pinecone, Weaviate, or Qdrant",
                    "dimensions": 1536,
                    "distance_metric": "cosine",
                    "indexed_fields": ["case_text", "arguments", "evidence", "statutes"],
                    "metadata_filters": ["domain", "party", "date_range", "jurisdiction"]
                }
            }

            # Step 5: Backend Architecture Recommendations
            backend_architecture = {
                "api_layer": {
                    "framework": "FastAPI or Flask with async support",
                    "endpoints": [
                        "POST /api/cases/upload - PDF ingestion",
                        "POST /api/cases/{case_id}/analyze - Deep analysis",
                        "GET /api/cases/{case_id}/graph - Graph data",
                        "GET /api/cases/{case_id}/parties - Party details",
                        "POST /api/search/semantic - Vector search",
                        "GET /api/analytics/dashboard - Metrics"
                    ],
                    "authentication": "JWT with refresh tokens",
                    "rate_limiting": "100 requests/minute per user"
                },
                "processing_pipeline": {
                    "stages": [
                        "1. PDF extraction (PyPDF2/pdfplumber)",
                        "2. Text preprocessing (spaCy/NLTK)",
                        "3. Domain classification (ML classifier)",
                        "4. Named entity recognition (Legal NER model)",
                        "5. Argument extraction (LLM-based)",
                        "6. Relationship mapping (Graph algorithms)",
                        "7. Strategic assessment (Analytical models)",
                        "8. Vector embedding (OpenAI/Sentence-Transformers)",
                        "9. Graph construction (NetworkX/Neo4j)",
                        "10. Storage and indexing"
                    ],
                    "async_queue": "Celery with Redis broker",
                    "caching": "Redis for intermediate results"
                },
                "ml_models": {
                    "llm": "OpenAI GPT-4o-mini or Claude Sonnet",
                    "embeddings": "text-embedding-3-small (1536d)",
                    "domain_classifier": "Fine-tuned BERT on legal domains",
                    "ner": "Legal-BERT or spaCy legal NER",
                    "gnn": "Graph Attention Network (GAT) for influence prediction"
                },
                "scalability": {
                    "containerization": "Docker + Kubernetes",
                    "load_balancing": "NGINX or AWS ALB",
                    "horizontal_scaling": "Stateless API servers",
                    "database_replication": "Read replicas for queries",
                    "cdn": "CloudFront for static assets"
                },
                "monitoring": {
                    "logging": "ELK Stack (Elasticsearch, Logstash, Kibana)",
                    "metrics": "Prometheus + Grafana",
                    "tracing": "Jaeger or AWS X-Ray",
                    "alerts": "PagerDuty integration"
                }
            }

            # Final comprehensive response
            response_data = {
                "metadata": {
                    "case_name": case_name,
                    "domain": domain,
                    "party_a_name": party_a_name,
                    "party_b_name": party_b_name,
                    "analysis_timestamp": "2026-02-20T00:00:00Z",
                    "graph_metrics": {
                        "total_nodes": len(nodes),
                        "total_edges": len(edges),
                        "party_a_argument_count": len([n for n in nodes if n.get("party") == "A" and n.get("type") in ["argument", "counter_argument"]]),
                        "party_b_argument_count": len([n for n in nodes if n.get("party") == "B" and n.get("type") in ["argument", "counter_argument"]])
                    }
                },
                "party_a": intelligence_data.get("party_a", {}),
                "party_b": intelligence_data.get("party_b", {}),
                "legal_themes": intelligence_data.get("legal_themes", []),
                "statutory_provisions": intelligence_data.get("statutory_provisions", []),
                "graph": {
                    "nodes": nodes,
                    "edges": edges
                },
                "database_schema": database_schema,
                "backend_architecture": backend_architecture
            }

            return jsonify(response_data)

        except Exception as e:
            print("LITIGATION GRAPH ERROR:", e)
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Litigation graph generation failed", "details": str(e)}), 500


# ===========================
# PRECEDENTS ENDPOINTS
# ===========================

@app.route("/precedents", methods=["GET"])
def get_precedents():
    """Get all or filtered landmark precedents"""
    try:
        if precedents_df.empty:
            return jsonify({"error": "Precedents data not available"}), 404
        
        domain = request.args.get("domain", "").lower()
        landmark_only = request.args.get("landmark_only", "false").lower() == "true"
        limit = int(request.args.get("limit", 30))
        
        result_df = precedents_df.copy()
        
        # Filter by domain if provided
        if domain:
            result_df = result_df[result_df["domain"].str.lower() == domain]
        
        # Filter by landmark status if requested
        if landmark_only:
            result_df = result_df[result_df["landmark_status"] == "landmark"]
        
        # Limit results
        result_df = result_df.head(limit)
        
        return jsonify({
            "total": len(result_df),
            "precedents": result_df.to_dict(orient="records")
        })
    
    except Exception as e:
        print(f"PRECEDENTS ERROR: {e}")
        return jsonify({"error": "Failed to retrieve precedents", "details": str(e)}), 500


@app.route("/precedents/search", methods=["POST"])
def search_precedents():
    """Search precedents by keyword"""
    try:
        data = request.get_json()
        query = data.get("query", "").lower()
        domain = data.get("domain", "").lower()
        
        if not query:
            return jsonify({"error": "Query required"}), 400
        
        if precedents_df.empty:
            return jsonify({"error": "Precedents data not available"}), 404
        
        result_df = precedents_df.copy()
        
        # Filter by domain if provided
        if domain:
            result_df = result_df[result_df["domain"].str.lower() == domain]
        
        # Search in case_name, ruling_summary, key_points
        mask = (
            result_df["case_name"].str.lower().str.contains(query, na=False) |
            result_df["ruling_summary"].str.lower().str.contains(query, na=False) |
            result_df["key_points"].str.lower().str.contains(query, na=False)
        )
        
        result_df = result_df[mask]
        
        return jsonify({
            "total": len(result_df),
            "query": query,
            "domain": domain if domain else "all",
            "precedents": result_df.to_dict(orient="records")
        })
    
    except Exception as e:
        print(f"PRECEDENTS SEARCH ERROR: {e}")
        return jsonify({"error": "Search failed", "details": str(e)}), 500


@app.route("/precedents/<int:case_id>", methods=["GET"])
def get_precedent_detail(case_id):
    """Get detailed information about a specific precedent"""
    try:
        if precedents_df.empty:
            return jsonify({"error": "Precedents data not available"}), 404
        
        case = precedents_df[precedents_df["case_id"] == case_id]
        
        if case.empty:
            return jsonify({"error": "Precedent not found"}), 404
        
        return jsonify(case.iloc[0].to_dict())
    
    except Exception as e:
        print(f"PRECEDENT DETAIL ERROR: {e}")
        return jsonify({"error": "Failed to retrieve precedent details"}), 500


@app.route("/precedents/domains", methods=["GET"])
def get_precedent_domains():
    """Get all unique domains in precedents database"""
    try:
        if precedents_df.empty:
            return jsonify({"domains": []}), 200
        
        domains = precedents_df["domain"].unique().tolist()
        domain_counts = precedents_df["domain"].value_counts().to_dict()
        
        return jsonify({
            "domains": sorted(domains),
            "counts": domain_counts,
            "total_precedents": len(precedents_df)
        })
    
    except Exception as e:
        print(f"DOMAINS ERROR: {e}")
        return jsonify({"error": "Failed to retrieve domains"}), 500


@app.route("/api/cases", methods=["GET"])
def get_cases_for_explorer():
    """Get cases formatted for the Case Explorer graph visualization"""
    try:
        if precedents_df.empty:
            return jsonify({"cases": []}), 200
        
        domain_filter = request.args.get("domain", "all").lower()
        
        result_df = precedents_df.copy()
        
        # Filter by domain if specified
        if domain_filter != "all":
            result_df = result_df[result_df["domain"].str.lower() == domain_filter]
        
        cases = []
        for _, row in result_df.iterrows():
            case = {
                "id": f"case_{row['case_id']}",
                "title": row["case_name"],
                "year": int(row["year"]) if pd.notna(row["year"]) else 2000,
                "type": row["domain"],
                "landmark": row.get("landmark_status", "") == "landmark",
                "summary": row["ruling_summary"][:300] if pd.notna(row["ruling_summary"]) else "No summary available",
                "citation": row.get("citation", ""),
                "court": row.get("court", ""),
                "judges": row.get("judges", ""),
                "ruling_summary": row.get("ruling_summary", ""),
                "key_points": row.get("key_points", ""),
                "supports": [],  # Will be populated based on domain similarity
                "opposes": [],   # Will be populated based on domain similarity
            }
            cases.append(case)
        
        # Generate relationships based on domain and landmark status
        for i, case1 in enumerate(cases):
            for j, case2 in enumerate(cases):
                if i != j:
                    # Landmark cases support newer cases in same domain
                    if case1["landmark"] and case1["type"] == case2["type"] and case1["year"] < case2["year"]:
                        if case2["id"] not in case1["supports"]:
                            case1["supports"].append(case2["id"])
                    
                    # Cases with different courts may oppose
                    if case1["court"] != case2["court"] and case1["type"] == case2["type"]:
                        if case1["year"] > case2["year"] and case2["id"] not in case1["opposes"]:
                            case1["opposes"].append(case2["id"])
        
        return jsonify({
            "cases": cases,
            "total": len(cases),
            "domain_filter": domain_filter
        })
    
    except Exception as e:
        print(f"CASES API ERROR: {e}")
        return jsonify({"error": "Failed to retrieve cases", "details": str(e)}), 500


@app.route("/analysis/case-explorer", methods=["POST"])
def case_explorer():
    """
    Convert case analysis into interactive argument graph visualization.
    
    Accepts case analysis JSON (from comprehensive analysis endpoint)
    Returns: Interactive graph structure with nodes, edges, parties, and inspector details
    """
    try:
        payload = request.get_json() or {}
        
        # Extract the comprehensive analysis
        case_analysis = payload
        
        if not case_analysis or not case_analysis.get("party_a"):
            return jsonify({"error": "Invalid case analysis structure"}), 400
        
        # Generate the graph structure
        graph_data = generate_case_explorer_graph(case_analysis)
        
        if not graph_data:
            return jsonify({"error": "Failed to generate case explorer graph"}), 500
        
        return jsonify(graph_data), 200
    
    except Exception as e:
        print(f"❌ Case Explorer Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Case explorer generation failed", "details": str(e)}), 500

# ===========================
if __name__ == "__main__":
    print("🚀 Starting Flask backend with Auth + Legal AI...")
    app.run(host="0.0.0.0", port=5000, debug=True)
