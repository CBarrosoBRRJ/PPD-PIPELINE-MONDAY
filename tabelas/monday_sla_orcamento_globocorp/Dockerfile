FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY compartilhado /build/comum
COPY tabelas/monday_sla_orcamento_globocorp/pyproject.toml ./
COPY tabelas/monday_sla_orcamento_globocorp/src ./src
RUN pip install --no-cache-dir /build/comum . && useradd --uid 10001 --create-home pipeline
COPY tabelas/monday_sla_orcamento_globocorp/sql ./sql
USER pipeline
ENTRYPOINT ["sla-pipeline"]
CMD ["daily"]
