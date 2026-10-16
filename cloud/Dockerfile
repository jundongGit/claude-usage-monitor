# Build context is the repository root: the dashboard template is shared with the app.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY cloud/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY report_template.py cloud/server.py ./
RUN useradd -u 10001 -m app && mkdir /data && chown app /data
USER app
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
