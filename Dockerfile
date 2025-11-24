FROM python:3.11-slim

# Create non-root user
ARG USER=app
ARG GROUP=app
RUN groupadd -r $GROUP && useradd -r -g $GROUP $USER

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Avoid writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only dependency manifests first for better caching
COPY requirements.txt /app/

# Install build deps and install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc build-essential libssl-dev libffi-dev \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && apt-get remove -y gcc build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Ensure Python can import the package from src and initialize the DB
ENV PYTHONPATH=/app/src
# Run DB initialization using the venv python so events_db.sqlite is created in the image
RUN /opt/venv/bin/python -m multi_tool_agent.setup_events_db

# Ensure proper permissions
RUN chown -R $USER:$GROUP /app

USER $USER

# Default command runs tests (override as needed)
CMD ["/opt/venv/bin/python", "-m", "pytest", "-q"]
