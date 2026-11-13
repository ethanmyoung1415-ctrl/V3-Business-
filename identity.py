"""Local identity and session groundwork for V3.

NOT connected to the HTTP dashboard and NOT production authentication.
The account registry is a testable authorization primitive. Deployments need
TLS, secure cookies, rate limiting, MFA, audit reviews and threat modeling.
"""
import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid

ROLE_OPERATOR="operator"
ROLE_CUSTOMER="customer"
MIN_PASSWORD=12
TTL_SECONDS=3600

def setup(db):
    with sqlite3.connect(db) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS local_users(
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('operator','customer')),
            customer_id TEXT,
            active INTEGER NOT NULL CHECK(active IN (0,1)),
            created_epoch INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS local_sessions(
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_epoch INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES local_users(id));
        CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON local_sessions(expires_epoch);
        """)

def _name(name):
    if not isinstance(name,str):raise ValueError("username required")
    normalized=name.strip().casefold()
    if len(normalized)<3 or len(normalized)>80 or not all(c.isalnum() or c in "._-" for c in normalized):
        raise ValueError("invalid username")
    return normalized

def _hash(password,salt):
    if not isinstance(password,str):raise ValueError("invalid password")
    return hashlib.scrypt(password.encode("utf-8"),salt=salt,n=2**14,r=8,p=1,dklen=32)

def create_user(db,username,password,role,customer_id=None):
    """Local administrative bootstrap only; never expose unauthenticated remotely."""
    setup(db)
    name=_name(username)
    if role not in (ROLE_OPERATOR,ROLE_CUSTOMER):raise ValueError("invalid role")
    if not isinstance(password,str) or not MIN_PASSWORD<=len(password)<=128:
        raise ValueError("password must be 12–128 characters")
    if role==ROLE_CUSTOMER:
        if not customer_id or str(uuid.UUID(customer_id))!=customer_id:
            raise ValueError("customer role requires a valid customer identifier")
    elif customer_id is not None:raise ValueError("operator may not be bound to a customer")
    salt=secrets.token_bytes(16)
    user_id=str(uuid.uuid4())
    digest=_hash(password,salt)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO local_users VALUES(?,?,?,?,?,?,?,?)",
                     (user_id,name,salt,digest,role,customer_id,1,int(time.time())))
    return {"id":user_id,"username":name,"role":role,"customer_id":customer_id}

def login(db,username,password):
    setup(db)
    name=_name(username)
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute("SELECT * FROM local_users WHERE username=? AND active=1",(name,)).fetchone()
        # Avoid a trivial username enumeration timing difference.
        salt=row["salt"] if row else bytes(16)
        expected=row["password_hash"] if row else bytes(32)
        digest=_hash(password,salt)
        if not row or not hmac.compare_digest(digest,expected):
            raise ValueError("invalid credentials")
        token=secrets.token_urlsafe(32)
        conn.execute("INSERT INTO local_sessions VALUES(?,?,?)",
            (hashlib.sha256(token.encode()).hexdigest(),row["id"],int(time.time())+TTL_SECONDS))
    return token

def authenticate(db,token):
    if not isinstance(token,str) or len(token)>256 or len(token)<20:
        raise ValueError("invalid session")
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    with sqlite3.connect(db) as conn:
        conn.row_factory=sqlite3.Row
        user=conn.execute("""SELECT u.id,u.username,u.role,u.customer_id
            FROM local_sessions s JOIN local_users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_epoch>? AND u.active=1""",
            (token_hash,int(time.time()))).fetchone()
        if not user:raise ValueError("session expired or invalid")
        return dict(user)

def authorize(principal,customer_id,operation):
    """Explicit permission for tenant-scoped actions. Defaults to denying."""
    if operation not in ("read_catalog","submit_update","review_change","approve_change","view_metrics"):
        raise PermissionError("unknown operation")
    if principal.get("role")==ROLE_OPERATOR:
        # Operator approvals still require separate audited business decisions.
        return True
    if principal.get("role")==ROLE_CUSTOMER and principal.get("customer_id")==customer_id:
        if operation in ("read_catalog","submit_update","view_metrics"):
            return True
    raise PermissionError("access denied")

def logout(db,token):
    if not isinstance(token,str):raise ValueError("invalid token")
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM local_sessions WHERE token_hash=?",
            (hashlib.sha256(token.encode()).hexdigest(),))
