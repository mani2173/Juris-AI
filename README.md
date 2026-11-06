Juris-AI

An AI-powered platform for legal research and case simulation. It uses natural language processing and machine learning to retrieve similar case law, generate legal insights, and support decision-making.

Team project. Original repository by the team lead: https://github.com/Priya-1514/Juris-AI This is my fork, kept to document my contribution.

My contribution
Backend development: built and worked on the Flask REST API (authentication, case search, precedent lookup, analysis and simulation endpoints, PDF upload).
Dataset gathering: collected and prepared the case-law data the system searches over (a judgments dataset of 5,000+ Indian court cases and a curated set of landmark precedents).
Supporting work: testing, documentation and other project tasks around the core build.
Features
Semantic search over case law using sentence embeddings and cosine similarity
Case analysis and outcome simulation endpoints
Precedent browsing and search by domain
Upload a PDF and analyse it (/upload-pdf)
Argument-graph "Case Explorer" for visualising a case's arguments
User registration, login and profile with JWT authentication
Tech stack
Area	Tools
Backend	Python, Flask, Flask-CORS
Auth	Flask-JWT-Extended, Flask-Bcrypt, SQLite
NLP / ML	sentence-transformers (all-MiniLM-L6-v2), scikit-learn, PyTorch, Transformers
Data	pandas, NumPy, CSV datasets, precomputed embeddings (pickle)
Documents	pypdf
LLM	OpenAI API (key supplied through .env)
Project structure
backend/
  app.py                 Flask app and all API routes
  case_explorer.py       builds the interactive argument graph
  embeddings.py          loads the embedding model
  build_embeddings.py    generates embeddings for the case dataset
  nlp_utils.py           text cleaning
  data/                  case datasets and precomputed embeddings
  requirements.txt
frontend/                user interface
API overview
Endpoint	Method	Purpose
/auth/register, /auth/login, /auth/profile	POST / POST / GET	User accounts
/analyze	POST	Analyse a case description
/simulate	POST	Simulate a case outcome
/analysis/case-explorer	POST	Argument graph for a case
/precedents, /precedents/search, /precedents/<id>, /precedents/domains	GET / POST	Browse and search precedents
/upload-pdf	POST	Upload and analyse a PDF
/api/cases	GET	List cases
Run the backend
bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # then add your own OpenAI API key (Mac/Linux: cp)
python app.py

To rebuild the case embeddings from the dataset:

bash
python build_embeddings.py
Credits

Built as a team project. Thanks to the team lead for the original repository and to all teammates.
