# Gemini Project Context: Kidney Genetics Database

This document provides an overview of the Kidney Genetics Database project, its structure, and key commands to assist Gemini in understanding and interacting with the codebase.

## Project Overview

The Kidney Genetics Database is a web application designed for curating and exploring genes related to kidney diseases. It features a Python/FastAPI backend, a Vue.js/Vuetify frontend, and a PostgreSQL database. The project is in an alpha stage of development.

### Key Technologies

*   **Backend**: Python, FastAPI, SQLAlchemy, Alembic, `uv` for environment management.
*   **Frontend**: JavaScript, Vue.js, Vite, Vuetify, Pinia, Axios.
*   **Database**: PostgreSQL.
*   **Containerization**: Docker, Docker Compose.
*   **Code Quality**: `ruff`, `black`, `mypy`, `pytest` for the backend, and `eslint`, `prettier` for the frontend.
*   **Scrapers**: A separate set of Python scripts for scraping diagnostic panels and literature data.

### Architecture

The application is composed of three main services:

1.  **`postgres`**: The PostgreSQL database.
2.  **`backend`**: The FastAPI application that provides the REST API and data processing pipeline.
3.  **`frontend`**: The Vue.js single-page application that provides the user interface.

These services can be run together using Docker Compose or in a hybrid mode where the database runs in Docker and the backend and frontend run locally.

## Building and Running

The project uses a `Makefile` to streamline common development tasks.

### Hybrid Development (Recommended)

This mode runs the database in a Docker container and the backend and frontend services on the local machine.

1.  **Start the database service:**
    ```bash
    make hybrid-up
    ```

2.  **Run the backend:**
    ```bash
    make backend
    ```
    The backend will be available at `http://localhost:8000`.

3.  **Run the frontend:**
    ```bash
    make frontend
    ```
    The frontend will be available at `http://localhost:5173`.

### Full Docker Development

This mode runs all services in Docker containers.

1.  **Start all services:**
    ```bash
    make dev-up
    ```
    *   Frontend: `http://localhost:3000`
    *   Backend: `http://localhost:8000`

2.  **Stop all services:**
    ```bash
    make dev-down
    ```

### Other Useful Commands

*   `make help`: Display all available `make` commands.
*   `make status`: Show the status of Docker services and local processes.
*   `make db-reset`: Reset the database and run all migrations.
*   `make lint`: Lint the backend code with `ruff`.
*   `make test`: Run the backend tests with `pytest`.
*   `cd frontend && npm run lint`: Lint the frontend code.

## Development Conventions

### Backend

*   **Dependency Management**: The backend uses `uv` to manage Python dependencies, which are defined in `backend/pyproject.toml`.
*   **Database Migrations**: Database schema changes are managed with Alembic. Migration scripts are located in `backend/alembic/versions`.
*   **Testing**: Backend tests are written with `pytest` and are located in the `backend/tests` directory.
*   **Code Style**: Code is formatted with `black` and linted with `ruff`.

### Frontend

*   **Dependency Management**: The frontend uses `npm` to manage JavaScript dependencies, which are defined in `frontend/package.json`.
*   **Code Style**: Code is formatted with `prettier` and linted with `eslint`.
*   **API Interaction**: The frontend communicates with the backend via a REST API. The API client is configured in `frontend/src/api/client.js`.

### Scrapers

*   The `scrapers` directory contains two subdirectories: `diagnostics` and `literature`.
*   Each scraper is designed to be run independently and has its own `README.md` with instructions.
*   The scrapers output JSON files that can be uploaded to the main application via the admin panel.

## Documentation

The `docs` directory contains extensive documentation about the project. Key documents include:

*   `docs/PROJECT_STATUS.md`: A high-level overview of the project's status.
*   `docs/architecture/`: Detailed information about the backend and database architecture.
*   `docs/development/`: Guides for setting up the development environment.
*   `docs/features/`: Descriptions of the application's features.
*   `CLAUDE.md`: A guide for AI assistants working with the codebase.