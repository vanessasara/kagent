FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY cert_manager ./cert_manager

# Install dependencies
RUN uv pip install --system -e .

# Run the agent
CMD ["python", "-m", "cert_manager.agent"]
