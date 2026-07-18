FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

ENV PORT=8000
EXPOSE 8000

# Command to run uvicorn dynamically binding to $PORT
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port $PORT"]
