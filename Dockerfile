# Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies including Google Chrome for Kaleido/Plotly
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

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the .chainlit configuration directory
COPY .chainlit .chainlit

# Copy chainlit.md
COPY chainlit.md chainlit.md

# Copy environment configuration
COPY .env .env

# Copy the application source code and utilities
COPY chatbot chatbot
COPY projectutils projectutils

# Copy pyproject.toml for package installation
COPY pyproject.toml pyproject.toml

# Create data directory structure and copy only essential files
RUN mkdir -p data/chatbot data/chroma-peterson
COPY data/chatbot data/chatbot

# Copy the public directory for custom CSS
COPY public public

# Install the project as a package to resolve imports
RUN pip install -e .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run the app
# The command `chainlit run chatbot/app.py` is run from the project root (/app in the container)
# `--host 0.0.0.0` makes the app accessible externally
CMD ["chainlit", "run", "chatbot/app.py", "--host", "0.0.0.0", "--port", "8000"]
