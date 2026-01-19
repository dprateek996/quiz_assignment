# ChapterIQ 📚

An AI-powered learning platform that transforms PDF chapters into interactive quizzes and provides an intelligent tutoring experience using Google's Gemini 2.0.

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![Vue.js](https://img.shields.io/badge/Vue.js-3-brightgreen?logo=vuedotjs)
![Prisma](https://img.shields.io/badge/Prisma-ORM-blueviolet?logo=prisma)
![Gemini](https://img.shields.io/badge/Gemini-2.0-orange?logo=google)

---

## ✨ Features

### 📖 PDF Chapter Management
- Upload PDF documents for AI processing
- Automatic content extraction and indexing via Gemini Files API
- Duplicate detection using SHA-256 content hashing (idempotency)

### 🤖 AI Tutor
- Chat with your uploaded chapters
- Get instant answers and explanations from the PDF content
- Summarization on demand

### 📝 Dynamic Quiz Generation
- Generate quizzes based on chapter content
- Multiple question types: MCQ, Short Answer, Numerical
- Three difficulty levels: Easy, Medium, Hard
- Context-aware quiz generation based on chat history

### 📊 Progress Tracking
- Mastery-based learning progress
- Quiz performance affects progress (penalties for low scores)
- Visual progress indicators on dashboard

### 📈 Analytics
- User performance tracking
- Chapter-level statistics
- Weak topic identification

## Personal Additions & Extra Touches

Apart from the required features in the assignment, I added a few extra things on my own to make the system more practical and production-ready:

- **Context-aware quizzes**  
  Quiz questions are not generated only from the PDF. If a student has interacted with the AI and spent more time on certain topics, those topics are intentionally emphasized in the quiz.

- **Duplicate PDF handling (cost saving)**  
  Added file hashing so if the same PDF is uploaded again, the system does not re-upload it to Gemini. It directly reuses the existing indexed chapter.

- **Proper request validation**  
  Added strict validation for quiz generation (difficulty, total questions, limits) so invalid or unnecessary requests don’t reach the AI.

- **Safe JSON handling**  
  Handled cases where the database already returns parsed JSON, preventing crashes due to double parsing.

- **Rate limiting on heavy endpoints**  
  Applied rate limits on PDF upload, quiz generation, and chat endpoints to avoid API misuse and unnecessary cost.


---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Vue.js 3, Bootstrap 5 |
| **Backend** | FastAPI (Python) |
| **Database** | PostgreSQL (Neon) |
| **ORM** | Prisma Client Python |
| **AI/LLM** | Google Gemini 2.0 Flash |
| **Rate Limiting** | SlowAPI |

---

## 📁 Project Structure

```
quiz_assignment/
├── frontend/
│   └── index.html          # Single-page Vue.js application
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Environment configuration
│   │   │   └── database.py     # Prisma database connection
│   │   ├── llm/
│   │   │   ├── gemini_client.py
│   │   │   └── prompts.py
│   │   ├── schemas/
│   │   │   └── quiz.py         # Pydantic request models
│   │   ├── services/
│   │   │   ├── chapter_service.py  # PDF upload & management
│   │   │   └── quiz_service.py     # Quiz generation & grading
│   │   └── main.py             # FastAPI application entry
│   │
│   ├── prisma/
│   │   └── schema.prisma       # Database schema
│   │
│   ├── requirements.txt
│   └── reset_app.py            # Utility to wipe all data
│
└── README.md
```

---

##  Getting Started

### Prerequisites

- Python 3.12+
- Node.js (optional, for serving frontend)
- PostgreSQL database (or use [Neon](https://neon.tech))
- Google Gemini API Key

### 1. Clone the Repository

```bash
git clone https://github.com/dprateek996/quiz_assignment.git
cd quiz_assignment
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate Prisma client
prisma generate
```

### 3. Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL="postgresql://user:password@host:5432/database?sslmode=require"
GEMINI_API_KEY="your-gemini-api-key"
```

### 4. Database Migration

```bash
prisma db push
```

### 5. Run the Backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### 6. Run the Frontend

Open `frontend/index.html` in a browser, or serve it:

```bash
# Using Python
cd frontend
python -m http.server 5500

# Or use VS Code Live Server extension
```

---

## 📡 API Endpoints

### Health Check
```
GET /health
```

### Chapters
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chapters` | Upload a PDF chapter |
| `GET` | `/api/dashboard/{user_id}` | Get user's chapter dashboard |
| `DELETE` | `/api/chapters/{chapter_id}` | Delete a chapter |
| `PUT` | `/api/chapters/{chapter_id}/progress` | Update reading progress |

### AI Tutor
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chapters/{chapter_id}/ask` | Ask a question about the chapter |

### Quizzes
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/quizzes/generate/{chapter_id}` | Generate a quiz |
| `POST` | `/api/quizzes/{quiz_id}/submit` | Submit quiz answers for grading |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/{user_id}/performance` | Get user performance stats |
| `GET` | `/api/chapters/{chapter_id}/analytics` | Get chapter analytics |

---

## 🔒 Rate Limits

| Endpoint | Limit |
|----------|-------|
| Upload Chapter | 5/minute |
| Ask Tutor | 20/minute |
| Generate Quiz | 10/minute |

---

## 🗄️ Database Schema

### Models

- **Chapter** - Stores uploaded PDF metadata and Gemini file reference
- **UserProgress** - Tracks user's mastery progress per chapter
- **Quiz** - Generated quiz with questions (JSON)
- **QuizAttempt** - User's quiz submission and scores


### Reset All Data
Wipes all chapters, quizzes, and progress from both database and Google Cloud:

```bash
python reset_app.py
```

---



## 👤 Author

**Prateek Dwivedi**

- GitHub: [@dprateek996](https://github.com/dprateek996)
