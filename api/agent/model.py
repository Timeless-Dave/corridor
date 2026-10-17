"""OpenAI Responses adapter. No API call occurs until a model method is invoked."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from agent.prompts import SYSTEM, data_block
from agent.schemas import INVESTIGATION_TOOLS, INTERPRETATION, VERDICT, ID, obj, function, validate


class ModelError(RuntimeError):
    pass


class OpenAIModel:
    def __init__(self,client=None,model=None):
        load_dotenv(Path(__file__).resolve().parents[2]/'.env')
        self.model=model or os.getenv('OPENAI_MODEL','gpt-4.1-mini')
        if client is None:
            key=os.getenv('OPENAI_API_KEY','').strip()
            if not key or key.lower() in ('placeholder','your-api-key','your_openai_api_key'):
                raise ModelError('Set OPENAI_API_KEY in the local .env before live model verification.')
            from openai import OpenAI
            client=OpenAI(api_key=key,timeout=45,max_retries=0)
        self.client=client
        self.pending=None

    def _request(self,inputs,tools,choice='required'):
        try:
            response=self.client.responses.create(model=self.model,instructions=SYSTEM,input=inputs,
                tools=tools,tool_choice=choice,parallel_tool_calls=False,max_output_tokens=2048,store=False)
            calls=[item for item in response.output if item.type=='function_call']
            if response.status!='completed' or len(calls)!=1:
                raise ValueError('Expected one completed function call.')
            call=calls[0]
            definition=next(t for t in tools if t['name']==call.name)
            args=validate(json.loads(call.arguments),definition['parameters'])
            return call.name,args,response.output,call.call_id
        except Exception:
            raise ModelError('OpenAI response failed or did not match the required schema.') from None

    def choose(self,context,findings):
        inputs=[{'role':'user','content':'Choose the next investigation tool.\n'+data_block({'context':context,'findings':findings})}]
        name,args,output,call_id=self._request(inputs,INVESTIGATION_TOOLS)
        self.pending=(inputs+[item.model_dump(exclude_none=True) for item in output],call_id,name)
        if name=='finish_investigation':
            self.pending=None
        return {'name':name,'params':args}

    def interpret(self,tool,params,result,allowed_citations):
        value={'tool':tool,'params':params,'result':result,'allowed_citations':sorted(allowed_citations)}
        if self.pending and self.pending[2]==tool:
            inputs,call_id,_=self.pending
            # Scope interpretation to this result, not the investigation history.
            inputs=[{'role':'user','content':'Interpret only the following tool result. Empty results mean no evidence and require no citations.'}]+[
                item for item in inputs if item.get('type')=='function_call'
            ]+[{'type':'function_call_output','call_id':call_id,'output':data_block(value)}]
        else:
            inputs=[{'role':'user','content':'Interpret this result.\n'+data_block(value)}]
        self.pending=None
        return self._request(inputs,[function('interpret_finding',INTERPRETATION,'Interpret the supplied result with supported citations.')],
            {'type':'function','name':'interpret_finding'})[1]

    def choose_policy(self,context):
        return self._request([{'role':'user','content':'Select an applicable policy.\n'+data_block(context)}],
            [function('select_policy',obj({'policy_id':ID}),'Select one policy ID from this corridor context.')],
            {'type':'function','name':'select_policy'})[1]['policy_id']

    def decide(self,context,findings):
        return self._request([{'role':'user','content':'Return the final proposed decision using retrieved company references.\n'+data_block({'context':context,'findings':findings})}],
            [function('submit_verdict',VERDICT,'Propose a verdict; the application validates and persists it.')],
            {'type':'function','name':'submit_verdict'})[1]
