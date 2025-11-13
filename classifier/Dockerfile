FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY rules.yaml ./
COPY fetch_rules.py ./
COPY entrypoint.sh ./

# Ensure entrypoint is executable and not CRLF
RUN chmod +x /app/entrypoint.sh &&     sed -i 's/\r$//' /app/entrypoint.sh

EXPOSE 8080
# Using sh explicitly also avoids exec bit issues on some filesystems
CMD ["sh","/app/entrypoint.sh"]
