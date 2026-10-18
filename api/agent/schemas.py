"""Strict model-facing read tools and structured control outputs."""
from jsonschema import Draft202012Validator

ID = {'type':'string','minLength':1,'maxLength':256}
IDS = {'type':'array','items':ID,'maxItems':200}
PATTERNS = ['circular_layering','fan_in_mule','shared_device','ajo_abuse','none']


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


READ_SCHEMAS = {
    'simulate_freeze': obj({'account_ids':IDS,'freeze_ids':IDS}),
    'min_freeze_set': obj({'account_ids':IDS,'k':{'type':'integer','minimum':1,'maximum':4}}),
    'shared_identifiers': obj({'account_id':ID}),
    'circular_flows': obj({'account_id':ID,'max_hops':{'type':'integer','minimum':2,'maximum':5}}),
    'fan_in': obj({'account_id':ID,'since':{'type':'integer','minimum':0},'max_amount':{'type':'number','exclusiveMinimum':0}}),
    'ajo_payout_pattern': obj({'pool_id':ID}),
    'ring_communities': obj({'account_ids':IDS}),
    'connected_cluster': obj({'account_id':ID}),
    'collector_rank': obj({'account_ids':IDS}),
    'link_to_known_bad': obj({'account_id':ID}),
    'who_knows': obj({'pattern':{'type':'string','enum':PATTERNS}}),
}
DESCRIPTIONS = {
    'simulate_freeze':'Measure specified observed accounts on a disposable graph copy. No live intervention; bounded historical routes only.',
    'min_freeze_set':'Measure a PageRank-ordered greedy freeze set on a disposable graph copy. Not a global minimum. Required before proposing FREEZE. Supply only accounts cited in this case.',
    'shared_identifiers':'Find accounts sharing devices or phones. Family sharing alone is not fraud.',
    'circular_flows':'Find chronological skimming cycles of 2–5 accounts within 72 hours.',
    'fan_in':'Count transfers below max_amount to a collector in the 48 hours after since.',
    'ajo_payout_pattern':'Find repeated pool recipients in consecutive rounds with shared-device evidence.',
    'ring_communities':'Run label propagation and return requested accounts; community membership is not fraud.',
    'connected_cluster':'Find identifier-only weak component; excludes transfer relationships.',
    'collector_rank':'Rank requested accounts by global transfer PageRank, not by risk.',
    'link_to_known_bad':'Find up to six-hop bidirectional paths to historical FREEZE accounts.',
    'who_knows':'Find employees who decided cases of this pattern.',
}
INTERPRETATION = obj({'text':{'type':'string','minLength':1,'maxLength':10000},'cited_ids':IDS})
VERDICT = obj({'verdict':{'type':'string','enum':['FREEZE','MONITOR','CLEAR']},
    'risk':{'type':'number','minimum':0,'maximum':1},
    'pattern':{'type':'string','enum':PATTERNS},'members':IDS,'policy_id':ID,
    'precedent_decision_id':ID,'assignee_employee_id':ID,
    'rationale':{'type':'string','minLength':1,'maxLength':10000}})


def validate(value,schema):
    import json
    # Also reject NaN/Infinity, which aren't valid JSON numbers.
    json.dumps(value,allow_nan=False)
    Draft202012Validator(schema).validate(value)
    return value


def function(name,schema,description):
    return {'type':'function','name':name,'description':description,'parameters':schema,'strict':True}


INVESTIGATION_TOOLS = [function(n,s,DESCRIPTIONS[n]) for n,s in READ_SCHEMAS.items()] + [
    function('finish_investigation',obj({}),'Finish exploration and retrieve mandatory company context before deciding.')]
