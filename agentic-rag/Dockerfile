FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install system dependencies for PyMuPDF/Chroma if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install python dependencies natively
RUN uv sync --no-dev --frozen

# Copy the rest of the application
COPY . .

# Run the FastAPI server
CMD ["uv", "run", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
