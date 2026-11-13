"""Offline, simulation-only customer workspaces.

Each mock customer gets a separate directory, SQLite DB, and staged input files.
This avoids accidental cross-customer mixing during testing. Not a substitute
for authentication, OS isolation, encrypted storage or production authorization.
"""
import os
import sqlite3
import uuid
from pathlib import Path
import engine
import operations

def root_dir(root):
    p=Path(root).resolve()
    p.mkdir(parents=True,exist_ok=True,mode=0o700)
    return p

def registry(root):
    p=root_dir(root)/"registry.sqlite3"
    with sqlite3.connect(p) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS simulated_customers(
            id TEXT PRIMARY KEY,name TEXT NOT NULL,created TEXT NOT NULL)""")
    return p

def create_customer(root,name):
    if not isinstance(name,str) or not name.strip() or len(name)>100:
        raise ValueError("mock customer name required, <=100 chars")
    id=str(uuid.uuid4())
    with sqlite3.connect(registry(root)) as c:
        c.execute("INSERT INTO simulated_customers VALUES(?,?,?)",
                  (id,name.strip(),engine.timestamp()))
    path=root_dir(root)/id
    path.mkdir(mode=0o700)
    return {"customer_id":id,"name":name.strip()}

def customer_db(root,customer):
    canonical=str(uuid.UUID(customer))
    if canonical!=customer:raise ValueError("invalid customer identifier")
    with sqlite3.connect(registry(root)) as c:
        match=c.execute("SELECT 1 FROM simulated_customers WHERE id=?",(customer,)).fetchone()
    if not match:raise ValueError("customer not found")
    directory=root_dir(root)/canonical
    if directory.is_symlink():raise ValueError("linked workspace rejected")
    directory.mkdir(exist_ok=True,mode=0o700)
    return directory/"work.sqlite3"

def enqueue(root,customer,baseline,update):
    db=customer_db(root,customer)
    return operations.enqueue(db,baseline,update)

def work_once(root,customer):
    db=customer_db(root,customer)
    return operations.work_once(db)

def review(root,customer,job):
    db=customer_db(root,customer)
    return engine.review(db,job)

def decide(root,customer,job,change,decision,actor,reason):
    db=customer_db(root,customer)
    if change not in {item["id"] for item in engine.review(db,job)["changes"]}:
        raise ValueError("change does not belong to the named customer job")
    return engine.decide(db,change,decision,actor,reason)
