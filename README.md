# HRMS Lite - Backend API

A simple and clean REST API for managing employees and tracking attendance. Built with FastAPI and PostgreSQL.

## What it does

This backend handles all the core HR operations:

- **Employee Management** - Add, view, and remove employees
- **Attendance Tracking** - Mark daily attendance and view records
- **Dashboard Stats** - Get quick overview of your team

## Tech Stack

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database (hosted on Aiven)
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation

## Getting Started

### Prerequisites

Make sure you have these installed:

- Python 3.11 or higher
- pip (Python package manager)
- PostgreSQL database (or use Aiven cloud like me)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/hrms-lite.git
   cd hrms-lite/backend
   ```
2 **Run**
 ```bash
  pip install -r requirements.txt
  .\.venv\Scripts\activate    
  py main.py or uvicorn main:app
```
