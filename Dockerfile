# Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Google Chrome for Kaleido/Plotly
# Do this early since system packages change less frequently
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Copy Python package configuration first for better caching
# Dependencies change less frequently than application code
COPY pyproject.toml .

# Install Python dependencies
# This layer will be cached unless pyproject.toml changes
RUN pip install --no-cache-dir -e .

# Copy configuration files
# These change less frequently than source code
COPY .chainlit .chainlit
COPY chainlit.md chainlit.md
COPY .env .env

# Create data directory structure and copy data files
# Data changes less frequently than source code
RUN mkdir -p data/chatbot data/chroma-peterson
COPY data/chatbot data/chatbot

# Copy static assets
COPY public public

# Copy application source code last
# Source code changes most frequently, so put it last for better caching
COPY chatbot chatbot
COPY projectutils projectutils

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run the app
# The command `chainlit run chatbot/app.py` is run from the project root (/app in the container)
# `--host 0.0.0.0` makes the app accessible externally
CMD ["chainlit", "run", "chatbot/app.py", "--host", "0.0.0.0", "--port", "8000"]
