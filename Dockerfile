FROM python:3.12-slim

WORKDIR /app

# Copy requirements generated from Poetry
COPY requirements.txt /app/requirements.txt

# Install runtime dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application sources
COPY . /app

# Expose and run
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]