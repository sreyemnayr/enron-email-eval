FROM python:3.13-slim

WORKDIR /code

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /code

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 --retries=10 -r requirements.txt

COPY . .

USER appuser

CMD ["python", "init_db.py"]