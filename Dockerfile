FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV DATABASE_PATH=/app/data
ENV DATABASE_URL=sqlite:////app/data/meal_planner.db

# Expose port
EXPOSE 8999

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8999"]