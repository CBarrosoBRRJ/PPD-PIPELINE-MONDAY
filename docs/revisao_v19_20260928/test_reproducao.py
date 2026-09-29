"""Local reproductions for review only. No cloud clients or mutations."""
import sys
from pathlib import Path
from datetime import datetime, UTC
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tabelas/monday_sla_orcamento/tests'))
from test_modelo_v19 import trajectory, run, one, attrs, CAL, CUT
import monday_sla_orcamento.modelo_v19 as m

def test_pausa_nao_e_retrabalho_nem_resposta_do_cliente():
    out=run(p=trajectory('p',[('Entrada',1),('Em Elaboração',2),('Aguardando Feedback',3),('Standby',4)]))
    p=one(out,'monday_sla_projeto','p')
    answer=one(out,'monday_sla_resposta_cliente','p')
    assert p['quantidade_retrabalhos']==0 and answer['desfecho']!='pediu_ajuste', (p['quantidade_retrabalhos'],answer['desfecho'])

def test_evento_da_meia_noite_nao_entra_no_dia_anterior():
    rows=trajectory('p',[('Entrada',1),('Em Elaboração',2),('Aguardando Feedback',3)])
    rows[2]['inicio']=datetime(2026,9,3,3,tzinfo=UTC)
    rows[1]['saida']=rows[1]['fim']=rows[2]['inicio']
    rows[1]['horas_uteis']=CAL.hours(rows[1]['inicio'],rows[1]['fim'])
    rows[1]['horas_corridas']=(rows[1]['fim']-rows[1]['inicio']).total_seconds()/3600
    out=run(p=rows)
    day=next(r for r in out['monday_sla_projeto_diario'] if r['data']=='2026-09-02')
    assert (day['status_fim_do_dia'],day['entregas_ate_o_dia']) == ('Em Elaboração',0), day

def test_serie_diaria_preserva_dias_em_standby_ate_o_corte():
    out=run(p=trajectory('p',[('Entrada',1),('Standby',2)]))
    days=out['monday_sla_projeto_diario']
    assert days[-1]['data']=='2026-09-27', days[-1]

def test_relacao_de_duplicado_ambiguo_nao_escolhe_primeiro():
    rows={pid:trajectory(pid,[('Entrada',1),('Em Elaboração',2),('Aguardando Feedback',3)]) for pid in ['original-a','original-b','copia']}
    ats={pid:attrs('[Marca] Talento') for pid in rows}
    for i,pid in enumerate(ats,1):ats[pid]['item_id_globocorp']=i
    ats['copia'].update(projeto_nome='[Marca] Talento [novo escopo]',nasceu_de_copia=True,status_copiado='Em Elaboração')
    out=m.build(rows,ats,cut=CUT,calendar=CAL)
    duplicate=one(out,'monday_sla_item_duplicado','copia')
    assert duplicate['projeto_relacionado'] is None, duplicate['projeto_relacionado']
