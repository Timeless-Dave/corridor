"""Small synthetic evaluation. Ground truth is never sent to the model."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from agent.loop import Investigation
from agent.model import OpenAIModel
from data.generate import generate
from data.load import load
from db import connect


def metrics(results):
    completed=[r for r in results if not r.get('error')]
    tp=fp=tn=fn=0
    for r in completed:
        predicted=r['verdict'] in ('FREEZE','MONITOR')
        expected=r['expected_ring_member']
        tp+=int(predicted and expected); fp+=int(predicted and not expected)
        tn+=int(not predicted and not expected); fn+=int(not predicted and expected)
    return {'tp':tp,'fp':fp,'tn':tn,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None, 'completed':len(completed),
            'errors':len(results)-len(completed),
            'freeze_on_rings':sum(r['verdict']=='FREEZE' and r['expected_ring_member'] for r in completed),
            'freeze_on_decoys':sum(r['verdict']=='FREEZE' and not r['expected_ring_member'] for r in completed),
            'ring_runs':sum(r['expected_ring_member'] for r in completed),
            'decoy_runs':sum(not r['expected_ring_member'] for r in completed)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'results.json')
    parser.add_argument('--model',default=None)
    parser.add_argument('--repeat',type=int,default=1,help='independent runs per flag, to measure verdict variance')
    parser.add_argument('--embedded',action='store_true',help='use an embedded FalkorDB (falkordblite) instead of FALKORDB_HOST')
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--heldout',default='',help='comma-separated unseen seeds; ids anonymized, planted transfers jittered (eval/worlds.py)')
    args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from baselines import rule_alerts, score
    if args.heldout:
        from worlds import world
        worlds=[(int(seed),*world(int(seed))) for seed in args.heldout.split(',')]
    else:
        data,truth=generate(42)
        worlds=[(42,data,truth['evaluation_flags'])]
    if args.embedded:
        import tempfile
        from redislite.falkordb_client import FalkorDB
        db=FalkorDB(tempfile.mkdtemp()+'/eval.db')
    def base_graph(name):
        if args.embedded:
            g=db.select_graph(name); g.client.list_graphs=db.list_graphs; return g
        return connect(graph_name=name)
    source_hash=hashlib.sha256()
    root=Path(__file__).resolve().parents[1]
    for file in sorted((root/'api').rglob('*')):
        if file.suffix in ('.py','.cypher'):
            source_hash.update(str(file.relative_to(root)).encode()); source_hash.update(file.read_bytes())
    report={'source_sha256':source_hash.hexdigest(),'seeds':[w[0] for w in worlds],'heldout':bool(args.heldout),'started_at':int(time.time()),'model':args.model or os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
            'scope':f'{len(worlds)} world(s) x 12 synthetic flags (4 planted patterns, 8 decoys); no real-world accuracy claim.',
            'positive_definition':'FREEZE or MONITOR compared with planted ring membership; shared identifiers alone do not establish fraud.',
            'isolation':'Each case starts from its own copy of the same seed graph, including one seeded historical case.',
            'repeat':args.repeat,'engine':'embedded FalkorDB (falkordblite)' if args.embedded else 'FalkorDB server',
            'results':[],'baselines':{}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock
    lock=Lock()
    for seed,data,flags in worlds:
        base=base_graph(f'corridor_eval_{uuid.uuid4().hex[:12]}_s{seed}')
        expected={f['account_id']:f['expected_ring_member'] for f in flags}
        report['baselines'][str(seed)]={name:score(alerted,expected) for name,alerted in rule_alerts(data,list(expected)).items()}
        try:
            load(base,data)
            def one(job):
                run,flag=job
                for attempt in range(8):
                    try:
                        graph=base.copy(base.name+'_case_'+uuid.uuid4().hex); break
                    except Exception as error:
                        # GRAPH.COPY forks the server; concurrent copies can be refused.
                        if 'fork' not in str(error) or attempt==7: raise
                        time.sleep(2+attempt*2)
                if args.embedded: graph.client.list_graphs=db.list_graphs
                record=dict(flag,run=run,seed=seed)
                try:
                    investigation=Investigation(graph,OpenAIModel(model=args.model))
                    result=investigation.run(flag['account_id'])
                    record.update(result)
                    record['trace']=investigation.events
                except Exception as error:
                    record['error']=type(error).__name__
                finally:
                    graph.delete()
                with lock:
                    report['results'].append(record)
                    report['metrics']=metrics(report['results'])
                    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
                    print(json.dumps({k:v for k,v in record.items() if k!='trace'}),flush=True)
            jobs=[(run,flag) for run in range(args.repeat) for flag in flags]
            with ThreadPoolExecutor(args.workers) as pool: list(pool.map(one,jobs))
        finally:
            base.delete()
    totals={}
    for per_world in report['baselines'].values():
        for name,m in per_world.items():
            t=totals.setdefault(name,{'tp':0,'fp':0,'fn':0,'tn':0})
            for k in t: t[k]+=m[k]
    report['baseline_totals']=totals
    report['finished_at']=int(time.time())
    report['base_graphs_deleted']=True
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report['metrics']),flush=True)
    print(json.dumps(totals),flush=True)

if __name__=='__main__': main()
