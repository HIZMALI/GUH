FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 gridsentinel
COPY pytest.ini ./
COPY apps/api ./apps/api
COPY services ./services
COPY edge ./edge
COPY data/synthetic ./data/synthetic
COPY data/scenarios ./data/scenarios
COPY tests ./tests
COPY scripts ./scripts
USER gridsentinel
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
