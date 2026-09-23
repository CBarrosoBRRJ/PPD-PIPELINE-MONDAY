FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY tabelas/monday_sla_orcamento_globocorp/pyproject.toml /build/sla/pyproject.toml
COPY tabelas/monday_sla_orcamento_globocorp/src /build/sla/src
COPY orquestracao/pyproject.toml /build/orquestracao/pyproject.toml
COPY orquestracao/src /build/orquestracao/src
COPY tabelas/monday_sla_orcamento_viu2/pyproject.toml /build/historico/pyproject.toml
COPY tabelas/monday_sla_orcamento_viu2/src /build/historico/src
COPY tabelas/monday_log_viu2/pyproject.toml /build/log/pyproject.toml
COPY tabelas/monday_log_viu2/src /build/log/src
COPY tabelas/monday_sla_orcamento/pyproject.toml /build/consolidado/pyproject.toml
COPY tabelas/monday_sla_orcamento/src /build/consolidado/src
COPY compartilhado/pyproject.toml /build/comum/pyproject.toml
COPY compartilhado/src /build/comum/src
RUN pip install --no-cache-dir /build/comum /build/sla /build/log /build/historico /build/consolidado /build/orquestracao && pip check \
    && useradd --uid 10001 --create-home pipeline
COPY orquestracao/deploy/pipelines.json /app/pipelines.json
RUN chmod 0644 /app/pipelines.json
USER pipeline
ENTRYPOINT ["pipeline-monday"]
CMD ["plan", "--manifest", "/app/pipelines.json"]
