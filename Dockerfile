FROM python:3.12-slim
# libfribidi0 lets Pillow's RAQM engine shape Devanagari (Hindi/Marathi). Without it conjuncts break.
RUN apt-get update && apt-get install -y --no-install-recommends libfribidi0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
# Web service default. The Render Workflow service overrides this with: python -m pipeline.workflow
CMD ["sh", "-c", "uvicorn web.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
