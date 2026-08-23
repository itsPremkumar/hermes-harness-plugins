FROM python:3.12-slim
WORKDIR /srv
COPY . .

# Run unprivileged
RUN useradd --create-home appuser
USER appuser

# Container orchestration health signal
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status==200 else 1)"

CMD ["python", "app.py"]
