FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Hugging Face Spaces default port is 7860
EXPOSE 7860

# Command to run uvicorn
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "7860"]
