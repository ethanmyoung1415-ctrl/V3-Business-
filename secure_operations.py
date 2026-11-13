"""Authentication-gated *local* mock customer operations.

Designed for tests and future service APIs. The existing localhost dashboard
does not use this yet. No customer upload endpoints or hosted accounts exist.
"""
import identity
import metrics
import workspaces

def _principal(accounts_db,token,customer,action):
    principal=identity.authenticate(accounts_db,token)
    identity.authorize(principal,customer,action)
    return principal

def submit(accounts_db,token,root,customer,baseline,update):
    _principal(accounts_db,token,customer,"submit_update")
    return workspaces.enqueue(root,customer,baseline,update)

def read_job(accounts_db,token,root,customer,job):
    _principal(accounts_db,token,customer,"read_catalog")
    return workspaces.review(root,customer,job)

def read_status(accounts_db,token,root,customer):
    _principal(accounts_db,token,customer,"view_metrics")
    db=workspaces.customer_db(root,customer)
    return metrics.snapshot(db)

def decide(accounts_db,token,root,customer,job,change,decision,reason):
    principal=_principal(accounts_db,token,customer,"approve_change")
    return workspaces.decide(root,customer,job,change,decision,
                             principal["username"],reason)
