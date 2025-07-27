# Dockerfile for a uv-based project

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Set environment variables for the virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies: git, curl (for Node), and Node.js
RUN apt-get update && \
    apt-get install -y git curl --no-install-recommends && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs --no-install-recommends && \
    npm install -g @modelcontextprotocol/inspector@0.15.0 && \
    rm -rf /var/lib/apt/lists/*

# Install uv globally
RUN pip install uv

# Create the virtual environment
RUN uv venv

# Copy your project definition and source code
COPY pyproject.toml /app/
COPY ./src /app/src
COPY ./.env /app/.env

# Install the project and its dependencies from pyproject.toml
RUN uv pip install .