# AI Logistics Agent 🚚📦

An AI-driven multi-agent logistics and supply chain optimization platform built with **FastAPI**, **SQLAlchemy**, and **Pydantic**.

---

## 🌟 Key Features

- **Order Management**: Create, track, and manage customer orders.
- **Inventory Tracking**: Monitor stock levels across multiple fulfillment centers and warehouses.
- **Intelligent Allocation**: Smart allocation algorithms to balance load and reduce transit distance.
- **Dispatch & Logistics Recommendation**: Vehicle fleet assignments and route optimization based on payload constraints, refrigeration requirements, and transit hours.
- **Interactive API Documentation**: Built-in Swagger UI and ReDoc for testing and integration.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone <YOUR_GITHUB_REPO_URL>
   cd "AI logistic agent"
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1   # On Windows
   # source venv/bin/activate    # On Linux / macOS
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Environment Variables:**
   Copy the example `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   Configure any desired variables (OpenAI API key, port, database URL, etc.).

---

## 🏃 Running the Application

### Method 1: Using `run.py`
```bash
python run.py
```

### Method 2: Using Uvicorn CLI
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📖 API Documentation

Once the server is running, you can explore the interactive API docs:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📁 Project Structure

```
├── app/
│   ├── agents/         # Multi-agent AI logic and LLM integrations
│   ├── api/            # API routing and endpoint handlers
│   ├── core/           # Configuration and environment settings
│   ├── database/       # Database session and models
│   ├── models/         # SQLAlchemy ORM models
│   ├── schemas/        # Pydantic data validation schemas
│   ├── services/       # Business logic and optimization services
│   └── main.py         # FastAPI application entrypoint
├── run.py              # Root runner script
├── main.py             # Alternative runner entrypoint
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── .gitignore          # Git ignore rules
```

---

## 📄 License
MIT License
