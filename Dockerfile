# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables to optimize Python performance in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py

# Set working directory inside container
WORKDIR /app

# Copy system dependencies list first to leverage Docker layer caching
COPY requirements.txt .

# Install Python package dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code into the container
COPY . /app/

# Expose standard Flask port
EXPOSE 5000

# Default entry point command to start Flask application
CMD ["python", "app.py"]
