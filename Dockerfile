FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright (Debian Trixie compatible)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && apt-get clean

# Install Playwright dependencies with correct package names
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libxshmfence1 \
    libx11-xcb1 \
    libxtst6 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxss1 \
    libxxf86vm1 \
    libglib2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libfreetype6 \
    libgcc-s1 \
    libgtk-3-0 \
    libnspr4 \
    libxcb-dri3-0 \
    libxcb-sync1 \
    libxcb-present0 \
    libgl1-mesa-dri \
    libgdk-pixbuf-2.0-0 \
    libxcb-shm0 \
    libxcb-xfixes0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application
COPY . .

# Set environment variables
ENV HEADLESS_MODE=true
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "soul.py"]