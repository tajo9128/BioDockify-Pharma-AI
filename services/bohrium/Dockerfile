FROM python:3.11-slim

WORKDIR /app

RUN pip install bohr-agent-sdk

COPY bohrium_mcp_service.py .

EXPOSE 7000

CMD ["python", "bohrium_mcp_service.py"]
