FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV NAMESPACE=qdrant
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000
ENV FASTMCP_TRANSPORT=streamable-http

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn qdrant_mcp.server:app --host \"$FASTMCP_HOST\" --port \"$FASTMCP_PORT\""]
