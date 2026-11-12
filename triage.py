"""Deterministic V3 catalog triage. Never approves or exports work."""
from decimal import Decimal, InvalidOperation

def _decimal(text):
    try:
        value=Decimal(str(text))
        return value if value.is_finite() else None
    except (ValueError,InvalidOperation):
        return None

def assess_change(change):
    field=change["field"];old=change["old"];new=change["new"]
    result={"change_id":change["id"],"sku":change["sku"],"field":field,
            "status":change["status"],"evidence":{"previous":old,"proposed":new}}
    if field=="price":
        a,b=_decimal(old),_decimal(new)
        if a is None or b is None or a<0 or b<0:
            risk,action,message="critical","hold","Invalid pricing; require corrected supplier data."
        elif a==0:
            risk,action,message="high","verify","Prior price is zero; confirm intended price and currency."
        else:
            pct=abs((b-a)/a*100)
            result["evidence"]["percent_change"]=str(pct.quantize(Decimal("0.01")))
            if pct>25:
                risk,action,message="high","verify","Price changed over 25%; verify source and margin."
            else:
                risk,action,message="medium","review","Check price against supplier and customer rules."
    elif field=="stock":
        if new=="0":
            risk,action,message="high","verify","Valid zero-stock update; confirm supplier availability."
        else:
            risk,action,message="low","review","Confirm SKU mapping and stock count."
    elif field=="title":
        risk,action,message="medium","review","Confirm title change against current product and supplier."
    else:
        risk,action,message="critical","hold","Unsupported field; do not apply."
    return result|{"risk":risk,"recommendation":action,"explanation":message}

def assess_hold(hold):
    reason=str(hold.get("reason","")).lower()
    risk="critical" if any(x in reason for x in ("duplicate","invalid","unknown")) else "high"
    return {"sku":hold.get("sku"),"field":hold.get("field"),"line":hold.get("line"),
            "risk":risk,"recommendation":"hold","source_reason":hold.get("reason",""),
            "explanation":"Correct source data and submit a new job. Never auto-approve this record."}

def report(db,job_id):
    import engine
    review=engine.review(db,job_id)
    changes=[assess_change(x) for x in review["changes"]]
    holds=[assess_hold(x) for x in review["holds"]]
    counts={risk:sum(x["risk"]==risk for x in changes+holds)
            for risk in ("critical","high","medium","low")}
    return {"job_id":job_id,"summary":{"changes":len(changes),"unresolved_holds":len(holds),
            "pending_decisions":sum(x["status"]=="pending" for x in review["changes"]),
            "risk_counts":counts,"requires_human":bool(holds or any(x["status"]=="pending" for x in review["changes"]))},
            "holds":holds,"changes":changes,
            "disclaimer":"Rule-based triage only; no AI approval or customer-store actions."}
