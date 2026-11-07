FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    HOST=0.0.0.0 \
    PORT=5050

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 libraw20 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-runtime.txt /tmp/requirements-runtime.txt

# Use a CPU wheel in this generic container; Android delegate/NPU timing is a separate device test.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /tmp/requirements-runtime.txt

COPY app.py isp.py model.py cnilut.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY models/mod_isp.pt models/sidd_srgb_nafnet_lite.pt models/nilutx3style.pt ./models/
COPY third_party/modular_neural_isp/ ./third_party/modular_neural_isp/

RUN useradd --system --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 5050
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/api/status',timeout=4)" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "--threads", "1", "--timeout", "120", "app:app"]
