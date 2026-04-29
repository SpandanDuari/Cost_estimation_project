# Multi-stage build: builder stage
FROM python:3.9-slim as builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set PATH to use pip-installed binaries
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app.py .
COPY templates/ templates/

# Expose port (adjust if your Flask app uses a different port)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/').read()" || exit 1

# Run the Flask application
CMD ["python", "-u", "app.py"]
