"""Bounded investigation orchestration; graph writes belong to this code, not the model."""
import argparse
import json
import time
import uuid
from agent.tools import CorridorTools, query_records
from agent.schemas import READ_SCHEMAS, INTERPRETATION, VERDICT, validate
from agent.guardrails import candidate_ids, positive_evidence, apply
from agent.model import OpenAIModel, ModelError
from db import connect, DatabaseError


class InvestigationError(RuntimeError):
    def __init__(self,case_id):
        self.case_id=case_id
        super().__init__('Database operation failed; case may remain open. Inspect it before retrying.')


class Investigation:
    def __init__(self,graph,model,on_event=None):
        self.graph=graph
        self.tools=CorridorTools(graph)
        self.model=model
        self.on_event=on_event or (lambda event: None)
        self.findings=[]
        self.events=[]
        self.steps=0
        self.sequence=0
        self.force_monitor=False
        self.case_id=None
        self.receipt=None
        self.started=False

    def prepare(self,account_id):
        if self.receipt is not None: raise ValueError('Case already prepared.')
        self.receipt=self.tools.open_case(account_id)
        self.prepared_account=account_id
        self.case_id=self.receipt['case_id']
        self.tools.case_id=self.case_id
        self.emit('opened',account_id=account_id)
        return self.case_id

    def emit(self,kind,**values):
        event={'type':kind,'case_id':self.case_id,**values}
        self.events.append(event)
        self.on_event(event)

    def note(self,text,details=None):
        self.sequence+=1
        query_records(self.graph,'record_system_finding',{'case_id':self.case_id,
            'finding_id':'finding_'+uuid.uuid4().hex,'step':self.sequence,'text':text,
            'details':json.dumps(details or {},allow_nan=False),'now':int(time.time())},readonly=False)
        self.emit('guardrail',text=text,details=details or {})

    def read(self,name,params,*,interpret=True):
        if self.steps>=12: raise RuntimeError('Investigation tool budget exhausted.')
        self.steps+=1
        error=False
        try:
            rows=self.tools.call(name,**params)
        except (ValueError,TypeError) as exc:
            rows=[]
            error=str(exc) if isinstance(exc,ValueError) else 'Invalid tool arguments.'
            # A rejected scratch-graph call is a bad parameter, not missing evidence.
            # Evidence-tool failures and rejected citations still force review.
            if name not in ('simulate_freeze','min_freeze_set'):
                self.force_monitor=True
        ids=candidate_ids(name,params,rows)
        resolved=query_records(self.graph,'resolve_citations',{'ids':ids}) if ids else []
        allowed={r['id'] for r in resolved}
        account_ids={r['id'] for r in resolved if 'Account' in r['labels']}
        source='model'
        try:
            if error:
                # Never let the model narrate a failed call as if it were an observation.
                source='deterministic'
                interpretation={'text':f'Tool call rejected: {error} No evidence was observed.','cited_ids':[]}
            elif name=='prior_cases':
                source='deterministic'
                interpretation={'text':f'Retrieved {len(rows)} historical case records. Past verdicts are context, not fresh evidence of wrongdoing.',
                                'cited_ids':sorted(allowed)}
            elif name in ('min_freeze_set','simulate_freeze') and rows:
                source='deterministic'
                plan=rows[0]
                before,after=plan['before'],plan['after']
                frozen=', '.join(plan['freeze_ids']) or 'no accounts'
                interpretation={'text':f"Observed exposure (live graph): {before['senders_reaching_collector']} accounts reach {plan['collector']} with {before['inflow_volume']:,.0f} USD historical inflow and {before['cycles_remaining']} cycle paths. Hypothetical, in a disposable copy only: blocking {frozen} leaves {after['senders_reaching_collector']} accounts, {after['inflow_volume']:,.0f} USD, {after['cycles_remaining']} cycle paths. The live graph is unchanged. The applied order is a PageRank greedy heuristic. The exact minimum vertex cut is computed separately with FalkorDB max-flow and re-measured on a second copy. Bounded to 5 hops and 72 hours." + (f" Exact minimum vertex cut by FalkorDB max-flow: {', '.join(plan['min_cut']['accounts'])} ({plan['min_cut']['size']}), {'verified' if plan['min_cut'].get('verified') else 'not verified'} on a fresh copy." if plan.get('min_cut', {}).get('accounts') else ''),
                                'cited_ids':sorted(allowed)}
            elif name=='collector_rank' and rows:
                source='deterministic'
                interpretation={'text':f"PageRank ranked {len(rows)} observed accounts. Highest: {rows[0]['account']} ({rows[0]['score']:.6g}). This is structural centrality, not a fraud score.", 'cited_ids':sorted(allowed)}
            elif name=='ring_communities' and rows:
                source='deterministic'
                interpretation={'text':f"Label propagation placed the requested accounts in {len(rows)} communities. Shared community membership is structural context, not evidence of wrongdoing.", 'cited_ids':sorted(allowed)}
            else:
                if not interpret: raise ModelError('Deterministic handling requested.')
                interpretation=validate(self.model.interpret(name,params,rows,allowed),INTERPRETATION)
        except Exception:
            source='deterministic'
            if interpret: self.force_monitor=True
            interpretation={'text':('Tool input rejected.' if error else
                'No evidence returned.' if not rows else f'{name} returned {len(rows)} records; model interpretation unavailable.'),
                'cited_ids':[]}
        rejected=sorted(set(interpretation['cited_ids'])-allowed)
        if rejected: self.force_monitor=True
        cited=sorted(set(interpretation['cited_ids']) & allowed)
        self.sequence+=1
        self.tools.record_finding(self.case_id,self.sequence,interpretation['text'],name,params,cited,
            result=rows,rejected_citations=rejected,interpretation_source=source)
        finding={'step':self.steps,'tool':name,'params':params,'result':rows,'text':interpretation['text'],
                 'cited_ids':cited,'rejected_citations':rejected,'account_ids':sorted(account_ids),
                 'positive':positive_evidence(name,rows),'error':bool(error),'interpretation_source':source}
        self.findings.append(finding)
        self.emit('finding',**finding)
        return rows

    def run(self,account_id,corridor='US-NG'):
        if self.started: raise ValueError('Use a new Investigation instance for each case.')
        if self.receipt and self.prepared_account!=account_id: raise ValueError('Prepared account mismatch.')
        self.started=True
        try:
            return self._run(account_id,corridor)
        except DatabaseError:
            self.emit('error',text='Database operation failed; inspect the case before retrying.')
            raise InvestigationError(self.case_id) from None

    def _run(self,account_id,corridor):
        if self.receipt is None: self.prepare(account_id)
        receipt=self.receipt
        memory=self.read('prior_cases',{'account_id':account_id,'exclude_case_id':self.case_id},
                         interpret=receipt['account_exists'])
        if not receipt['account_exists']:
            self.note('Unknown account ID; closing CLEAR with an error, not a successful clearance.',{'error':'unknown_account'})
            query_records(self.graph,'close_unknown_case',{'case_id':self.case_id,'now':int(time.time())},readonly=False)
            result={'case_id':self.case_id,'verdict':'CLEAR','risk':0.0,'pattern':'none','error':'unknown_account',
                    'members':[],'steps':self.steps,'step_cap_reached':False}
            self.emit('closed',decision=result)
            return result
        prior_freeze=any(r['verdict']=='FREEZE' for r in memory)
        if prior_freeze: self.note('Prior FREEZE found; starting risk raised to 0.7.')
        metadata=query_records(self.graph,'account_context',{'account_id':account_id})[0]
        context={'account_id':account_id,'corridor':corridor,'account':metadata,'prior_freeze':prior_freeze,
                 'starting_risk':0.7 if prior_freeze else 0.0,
                 'suggested_since':max(0,(metadata['latest_transfer_ts'] or int(time.time()))-172800),
                 'remaining_steps':9}
        # Reserve two reads for mandatory corridor context and current precedents.
        while self.steps<10 and not self.force_monitor:
            context['remaining_steps']=10-self.steps
            try:
                action=self.model.choose(context,self.findings)
                name=action['name']
                if name=='finish_investigation': break
                if name not in READ_SCHEMAS: raise ValueError('Disallowed model tool.')
                params=validate(action['params'],READ_SCHEMAS[name])
            except Exception:
                self.force_monitor=True
                self.note('Model selection failed or requested a disallowed tool; review required.')
                break
            self.read(name,params)
        capped=self.steps==10
        if capped: self.note('Investigation step cap reached; reserving final two reads for company grounding.')
        company=self.read('corridor_context',{'corridor_code':corridor})
        policies=sorted({p['id'] for r in company for p in r['policies'] if p.get('id')})
        selected=None
        precedents=[]
        if policies:
            try:
                selected=self.model.choose_policy(company)
                if selected not in policies: raise ValueError('Policy outside corridor.')
            except Exception:
                selected=policies[0]
                self.force_monitor=True
                self.note('Invalid or unavailable model policy selection; using first applicable policy for review.')
            precedents=self.read('precedents',{'policy_id':selected})
        context.update({'company':company,'selected_policy_id':selected,'precedents':precedents,'step_cap_reached':capped})
        fallback={'verdict':'MONITOR','risk':0.7 if prior_freeze else 0.5,'pattern':'none','members':[account_id],
                  'policy_id':selected or 'unavailable',
                  'precedent_decision_id':precedents[0]['decision'] if precedents else 'unavailable',
                  'assignee_employee_id':company[0].get('lead_id') or 'unavailable' if company else 'unavailable',
                  'rationale':'Incomplete or invalid model response; analyst review required.'}
        try:
            proposed=validate(self.model.decide(context,self.findings),VERDICT)
        except Exception:
            proposed=fallback
            self.force_monitor=True
            self.note('Final model response unavailable or invalid; deterministic MONITOR fallback.')
        decision,reasons,grounded=apply(proposed,self.findings,account_id,company,precedents,
            prior_freeze=prior_freeze,force_monitor=self.force_monitor)
        grounded=grounded and decision['policy_id']==selected
        if reasons: self.note(' '.join(reasons),{'proposed_verdict':proposed['verdict'],'final_verdict':decision['verdict']})
        if grounded:
            try:
                self.tools.close_case(self.case_id,decision['verdict'],decision['risk'],decision['pattern'],
                    decision['policy_id'],decision['precedent_decision_id'],decision['assignee_employee_id'],decision['members'],
                    rationale=decision['rationale'],proposed_verdict=proposed['verdict'],
                    guardrail_reasons=reasons,step_cap_reached=capped)
            except ValueError:
                grounded=False
        if not grounded:
            self.note('Company references missing, mismatched, or stale; closing unrouted MONITOR for review.')
            query_records(self.graph,'close_review_case',{'case_id':self.case_id,'risk':max(decision['risk'],0.5),
                'reason':'Company grounding invalid; analyst review required.','step_cap_reached':capped,'now':int(time.time())},readonly=False)
            decision.update({'verdict':'MONITOR','risk':max(decision['risk'],0.5),'pattern':'none','error':'review_required',
                'policy_id':None,'precedent_decision_id':None,'assignee_employee_id':None})
        result={'case_id':self.case_id,**decision,'steps':self.steps,'step_cap_reached':capped,'guardrail_reasons':reasons}
        self.emit('closed',decision=result)
        return result


def main(argv=None,*,model=None,graph=None):
    parser=argparse.ArgumentParser(description='Investigate one synthetic account with fixed graph tools.')
    parser.add_argument('account_id')
    parser.add_argument('--corridor',default='US-NG',choices=['US-NG','NG-US'])
    parser.add_argument('--model',default=None)
    args=parser.parse_args(argv)
    try:
        provider=model if model is not None else OpenAIModel(model=args.model)
        database=graph if graph is not None else connect()
        Investigation(database,provider,on_event=lambda event: print(json.dumps(event,allow_nan=False),flush=True)).run(args.account_id,args.corridor)
        return 0
    except (ModelError,DatabaseError,InvestigationError) as e:
        print(json.dumps({'type':'error','message':str(e),'case_id':getattr(e,'case_id',None)}),flush=True)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
