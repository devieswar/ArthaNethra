# 🚀 Getting Started with ArthaNethra

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- **Node.js 20+** — [Download](https://nodejs.org/)
- **Docker & Docker Compose** — [Download](https://www.docker.com/products/docker-desktop)
- **Git** — [Download](https://git-scm.com/downloads)

## API Keys Required

1. **LandingAI API Key**
   - Sign up at [landing.ai](https://landing.ai/)
   - Get your API key from the dashboard
   - For hackathon: Use the provided hackathon credits

2. **AWS Credentials**
   - Create an AWS account at [aws.amazon.com](https://aws.amazon.com/)
   - Enable AWS Bedrock access
   - Create access keys from IAM

---

## Quick Start (5 minutes)

### 1. Clone the Repository

```bash
git clone https://github.com/devieswar/ArthaNethra.git
cd ArthaNethra
```

### 2. Set Up Environment Variables

Create a `.env` file in the root directory with your API keys:

**Required variables:**
```bash
LANDINGAI_API_KEY=your_actual_landingai_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
NEO4J_PASSWORD=arthanethra123  # Change this!
```

### 3. Start Infrastructure with Docker

```bash
# Start all services (Weaviate, Neo4j, Backend, Frontend)
docker-compose up -d

# Check if services are running
docker-compose ps
```

Expected output:
```
NAME                    STATUS    PORTS
arthanethra-backend     Up        0.0.0.0:8000->8000/tcp
arthanethra-frontend    Up        0.0.0.0:4200->4200/tcp
arthanethra-weaviate    Up        0.0.0.0:8080->8080/tcp
arthanethra-neo4j       Up        0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

### 4. Access the Application

- **Frontend:** http://localhost:4200
- **Backend API Docs:** http://localhost:8000/api/v1/docs
- **Weaviate:** http://localhost:8080
- **Neo4j Browser:** http://localhost:7474 (username: `neo4j`, password: `arthanethra123`)

---

## Development Setup (Local without Docker)

If you prefer to run services locally:

### Backend Setup

#### Option 1: Using UV (Recommended - 10x faster! ⚡)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

cd backend

# Install dependencies and create virtual environment (one command!)
uv sync

# Run backend
uv run uvicorn main:app --reload
```

#### Option 2: Using pip (Traditional)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn main:app --reload
```

Backend will run at: http://localhost:8000

**💡 Tip:** UV is 10-100x faster than pip. See [UV_SETUP.md](UV_SETUP.md) for details.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
ng serve
```

Frontend will run at: http://localhost:4200

### Database Setup (Local)

```bash
# Start only databases with Docker
docker-compose up -d weaviate neo4j t2v-transformers
```

---

## Testing the Application

### 1. Upload a Document

1. Navigate to http://localhost:4200/upload
2. Upload a sample financial document (PDF)
3. Click "Start Extraction" to process with LandingAI ADE

### 2. View Knowledge Graph

1. Go to http://localhost:4200/graph
2. See entities and relationships
3. Filter by entity type

### 3. Chat with AI

1. Go to http://localhost:4200/chat
2. Ask: "What are the high-risk variable-rate debts?"
3. View evidence-backed responses

### 4. Review Risks

1. Go to http://localhost:4200/risks
2. See detected financial risks
3. Click citations to view source evidence

---

## Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'weaviate'`

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

### Frontend won't start

**Error:** `Cannot find module '@angular/core'`

**Solution:**
```bash
cd frontend
npm install
```

### Weaviate connection error

**Error:** `Connection refused to http://localhost:8080`

**Solution:**
```bash
# Check if Weaviate is running
docker-compose ps weaviate

# Restart Weaviate
docker-compose restart weaviate

# Check logs
docker-compose logs weaviate
```

### Neo4j authentication error

**Error:** `Authentication failed`

**Solution:**
1. Open http://localhost:7474
2. Login with username: `neo4j`, password: `arthanethra123`
3. Change password if needed
4. Update `NEO4J_PASSWORD` in `.env`

### LandingAI API error

**Error:** `401 Unauthorized`

**Solution:**
- Check your API key in `.env`
- Verify key is active at landing.ai dashboard
- For hackathon: Ensure you're using hackathon credits

### AWS Bedrock error

**Error:** `Could not connect to Bedrock`

**Solution:**
- Verify AWS credentials in `.env`
- Check if Bedrock is enabled in your AWS region
- Ensure Claude 3 model access is granted

---

## Project Structure

```
ArthaNethra/
├── backend/                 # FastAPI backend
│   ├── services/           # Business logic
│   ├── models/             # Data models
│   ├── config.py           # Configuration
│   ├── main.py             # FastAPI app
│   └── requirements.txt    # Python dependencies
├── frontend/                # Angular frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/ # UI components
│   │   │   ├── services/   # API services
│   │   │   └── models/     # TypeScript models
│   │   └── environments/   # Environment configs
│   └── package.json        # Node dependencies
├── docs/                    # Documentation
├── docker-compose.yml       # Docker orchestration
└── README.md                # Main documentation
```

---

## Next Steps

1. **Read the Documentation**
   - [Architecture](docs/ARCHITECTURE.md) — Technical design
   - [API Documentation](docs/API.md) — Backend endpoints
   - [Project Overview](docs/PROJECT_OVERVIEW.md) — Detailed features

2. **Explore the Code**
   - Backend services in `backend/services/`
   - Frontend components in `frontend/src/app/components/`
   - Data models in both backend and frontend

3. **Customize**
   - Add new risk detection rules in `backend/services/risk_detection.py`
   - Create new UI components in `frontend/src/app/components/`
   - Extend API endpoints in `backend/main.py`

---

## Sample Documents

For testing, you can use:

1. **SEC 10-K Filings** — Download from [sec.gov](https://www.sec.gov/edgar/searchedgar/companysearch.html)
2. **Loan Agreements** — Sample contracts (ensure they're public/anonymized)
3. **Financial Statements** — PDF format

**Note:** For the hackathon demo, prepare 2-3 sample documents in advance.

---

## Production Deployment

For deploying to production:

1. **AWS ECS**
   ```bash
   # Build and push Docker images
   docker build -t arthanethra-backend ./backend
   docker build -t arthanethra-frontend ./frontend
   
   # Push to ECR
   # Deploy to ECS
   ```

2. **Environment Variables**
   - Store secrets in AWS Secrets Manager
   - Use environment-specific configs

3. **Database**
   - Host Weaviate on managed cluster
   - Use Neo4j Aura for production

---

## Support

- **Issues:** [GitHub Issues](https://github.com/devieswar/ArthaNethra/issues)
- **Documentation:** [docs/](docs/)
- **Hackathon:** Check hackathon Discord/Slack

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Happy coding! 🚀**

