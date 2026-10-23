# Browser test runner: Chromium + system deps from the official Playwright image
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
RUN pip install --no-cache-dir --break-system-packages playwright==1.55.0
WORKDIR /work
