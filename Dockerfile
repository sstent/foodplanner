# Multi-stage Dockerfile for FoodPlanner

# Build stage: Install dependencies
FROM python:3.11-slim AS builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies into a virtual environment
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage: Copy application code and installed dependencies
FROM python:3.11-slim

# Install runtime dependencies (if any needed beyond Python base)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/venv /app/venv

# Activate the virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Create data directory and set permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

# Copy application code
COPY . .

# Ensure appuser owns all files
RUN chown -R appuser:appuser /app

# Switch to non-root user
#USER appuser

# Set working directory to /app for the application
WORKDIR /app

# Set environment variables
ENV DATABASE_PATH=/app/data
ENV DATABASE_URL=sqlite:////app/data/meal_planner.db

# Verify directory ownership (for debugging)
RUN ls -ld /app/data && \
    touch /app/data/test_write.txt && \
    echo "Write test successful" > /app/data/test_write.txt

# Expose port (as defined in main.py)
EXPOSE 8999

# Run the application with uvicorn - fix host to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8999"]