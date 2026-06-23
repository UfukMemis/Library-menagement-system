# Library Management System

A full-stack Library Management System. It integrates the [Kaggle Books dataset](https://www.kaggle.com/datasets/saurabhbagchi/books-dataset), provides REST APIs, role-based authentication, borrowing/reservation workflows, analytics reports, and a Dockerized three-container architecture.
## Architecture
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Frontend   │────▶│   Backend   │────▶│  PostgreSQL  │
│  (Nginx)    │     │  (FastAPI)  │     │   Database   │
│  :8080      │     │  :8000      │     │   :5432      │
└─────────────┘     └─────────────┘     └──────────────┘
## Features
- **User management**: registration, login/logout, bcrypt password hashing, JWT auth
- **Roles**: Administrator, Librarian, Student (RBAC)
- **Book catalog**: import/clean Kaggle dataset, search & filter, availability tracking
- **Borrowing & returns**: due dates, overdue tracking, transaction history
- **Reservations**: queue unavailable titles, duplicate prevention
- **Reports**: most borrowed books, active users, overdue list, monthly stats
- **Docker**: frontend, backend, and database containers
## Quick Start (Docker)
1. Clone the repository and copy environment variables:
bash
cp .env.example .env
2. *(Optional)* Download the Kaggle dataset and place `Books.csv` in the `data/` folder:
bash
# Requires Kaggle API credentials (~/.kaggle/kaggle.json)
kaggle datasets download -d saurabhbagchi/books-dataset -p data --unzip
If no CSV is present, the backend seeds a sample inventory on first startup.
3. Start the stack:
bash
docker compose up --build
4. Open the application:
- **Frontend**: http://localhost:8080
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
### Default admin account
| Field    | Value              |
|----------|--------------------|
| Username | `admin`            |
| Password | `admin`        |
| Email    | `admin@gmail.com` |
## Local Development (without Docker)
bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://lms_user:lms_password@localhost:5432/library_db
python -m scripts.import_books
uvicorn app.main:app --reload
### Frontend
Serve the `frontend/` folder with any static server, or use Docker/nginx proxy to `/api`.
## Database Schema
| Table | Purpose |
|-------|---------|
| `users` | Accounts, hashed passwords, roles |
| `books` | ISBN, title, author, publisher, year, copy counts |
| `borrow_transactions` | Borrow/return lifecycle and status |
| `reservations` | Holds for unavailable books |
## REST API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Student self-registration |
| POST | `/auth/login` | OAuth2 password login (JWT) |
| POST | `/auth/logout` | Logout (client discards token) |
| GET | `/auth/me` | Current user profile |
| GET/POST | `/books` | List/create books |
| GET/PUT/DELETE | `/books/{isbn}` | Read/update/delete book |
| GET/POST | `/users` | List/create users (staff) |
| POST | `/borrow` | Borrow a book |
| POST | `/return` | Return a borrowed book |
| GET | `/transactions` | Borrow history |
| GET/POST | `/reservations` | List/create reservations |
| POST | `/reservations/{id}/cancel` | Cancel reservation |
| GET | `/reports` | Analytics dashboard data |
Interactive documentation is available at `/docs` (Swagger UI).
## Dataset 
The import script (`backend/scripts/import_books.py`):
- Normalizes ISBN values and removes invalid rows
- Cleans publication years and text fields
- Deduplicates by ISBN
- Loads books with configurable copy counts
## Project Structure
library-management-system/
├── backend/
│   ├── app/
│   │   ├── routers/      # REST endpoints
│   │   ├── services/     # Business logic
│   │   ├── models.py     # SQLAlchemy models
│   │   └── main.py
│   ├── scripts/
│   │   └── import_books.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   ├── nginx.conf
│   └── Dockerfile
├── data/
│   └── Books.csv         # Sample / Kaggle dataset
├── docker-compose.yml
└── README.md
