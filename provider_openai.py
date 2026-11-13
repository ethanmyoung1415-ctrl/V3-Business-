"""Optional OpenAI Responses API adapter for synthetic V3 advisory tests.

OFF BY DEFAULT. No API requests occur unless all three flags and model name
are explicitly supplied. Never use with real customer data in this version.
No tools, no store writes, no conversation persistence, no autonomous approvals.
"""
import json
import os
import advisor

SCHEMA={
    "type":"object",
    "properties":{
        "explanation":{"type":"string"},
        "verification_step":{"type":"string"},
    },
    "required":["explanation","verification_step"],
    "additionalProperties":False,
}

def enabled(environ=None):
    env=os.environ if environ is None else environ
    return (
        env.get("V3_LOCAL_DEV")=="1" and
        env.get("V3_ENABLE_AI_ADVICE")=="1" and
        env.get("V3_SYNTHETIC_DATA_ONLY")=="1"
    )

def build_provider(*,environ=None,client_factory=None):
    """Return a callable; never instantiate a network client without all gates."""
    env=os.environ if environ is None else environ
    if not enabled(env):
        raise RuntimeError("AI provider disabled; three explicit local flags required")
    key=env.get("OPENAI_API_KEY","")
    model=env.get("V3_AI_MODEL","")
    if not key or len(key)<10 or not model or len(model)>100:
        raise RuntimeError("explicit provider credentials and model required")
    if client_factory is None:
        # Optional dependency, imported only after explicit configuration.
        from openai import OpenAI
        client_factory=OpenAI
    client=client_factory(api_key=key,timeout=15.0,max_retries=0)
    def advise(request):
        if not isinstance(request,dict) or set(request)!={"system_policy","input","response_schema"}:
            raise ValueError("unexpected advice request")
        if len(json.dumps(request["input"]))>3500:
            raise ValueError("advice request exceeds synthetic data cap")
        response=client.responses.create(
            model=model,
            instructions=request["system_policy"],
            input=json.dumps(request["input"],sort_keys=True),
            max_output_tokens=500,
            store=False,
            tools=[],
            text={"format":{
                "type":"json_schema","name":"v3_catalog_advisory",
                "strict":True,"schema":SCHEMA,
            }},
        )
        if getattr(response,"status",None)!="completed":
            raise RuntimeError("model response incomplete or refused")
        raw=getattr(response,"output_text","")
        if not isinstance(raw,str) or len(raw)>4096:
            raise ValueError("missing or oversized response")
        return json.loads(raw)
    return advise
