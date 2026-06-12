# Use a slim Python 3.12 image
FROM python:3.12-slim-bookworm

# Copy the uv binary from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
# - PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# - PYTHONUNBUFFERED: Prevents Python from buffering stdout/stderr
# - UV_SYSTEM_PYTHON: Forces uv to install packages globally instead of requiring a virtualenv inside the container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for PostgreSQL adapter and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to take advantage of Docker caching
COPY requirements.txt /app/

# Install python dependencies using uv (ultra-fast installer)
RUN uv pip install --no-cache -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Expose port 8000 for Nginx or direct web traffic
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
