"""Ensaio real somente leitura; executar no venv do pacote, nunca imprime segredos."""
import json
import os
import subprocess
from datetime import UTC, datetime

from pipeline_monday.worker_consolidated import execute
from sls_orcamento_ppd.config import Settings


def main():
    result = subprocess.run([
        'gcloud', 'run', 'jobs', 'describe', 'pipeline-monday',
        '--project=gglobo-viu-dados-hdg-prd', '--region=us-central1', '--format=json'
    ], capture_output=True, text=True, check=True)
    job = json.loads(result.stdout)
    containers = job['spec']['template']['spec']['template']['spec']['containers']
    if len(containers) != 1:
        raise ValueError('Container ambiguo')
    # Le apenas o prefixo nao secreto; nao copia tokens ou referencia de secrets.
    prefix = next(e['value'] for e in containers[0]['env'] if e['name'] == 'VIU2_ARCHIVE_PREFIX')
    os.environ['VIU2_ARCHIVE_PREFIX'] = prefix
    settings = Settings(_env_file=None, bq_project='gglobo-viu-dados-hdg-prd',
        bq_dataset='viu_agenciamento', bq_table='monday_sla_orcamento_globocorp',
        gcs_bucket='gglobo-viu-dados-hdg-prd-ppd-pipeline-monday', gcs_prefix='sla_orcamento')
    print(json.dumps(execute(settings, datetime.now(UTC), cycles_check=True), indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'rehearsal_failed', 'error_type': type(error).__name__,
                          'data_modified': False}))
        raise SystemExit(1) from None
