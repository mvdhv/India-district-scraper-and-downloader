# Use Playwright's official Python image (contains browsers & deps)
FROM mcr.microsoft.com/playwright/python:latest

# Set working directory
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Make sure pip/tools are recent, install Python deps
RUN python3 -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Ensure Playwright browser binaries are installed (safe even if base image already has them)
RUN python3 -m playwright install --with-deps

# Copy application code
COPY . .

# Expose port env var
ENV PORT 5000

# Run the Flask server
CMD ["python3", "app.py"]
