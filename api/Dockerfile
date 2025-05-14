FROM python:3.12-slim

LABEL org.opencontainers.image.name="vertex/vertexmemory-mcp"

WORKDIR /usr/src/vertexmemory

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8765
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
