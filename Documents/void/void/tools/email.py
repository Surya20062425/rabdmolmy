"""Email tools — IMAP/SMTP via stdlib, no extra deps.

Credentials passed per-call or cached in ~/.void/config.json.
Always pass credentials at least once; subsequent calls reuse cached values.
"""

import imaplib
import json
import smtplib
import ssl
from email import message_from_bytes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

from void.config import ensure_home, load, save
from void.tools.registry import register

CONFIG = ensure_home() / "config.json"


def _tokenize(s):
    """Tokenize an IMAP ENVELOPE S-expression: parens, quoted strings, atoms."""
    toks, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            toks.append(c)
            i += 1
        elif c == '"':
            i += 1
            buf = []
            while i < n:
                if s[i] == "\\" and i + 1 < n:
                    buf.append(s[i + 1])
                    i += 2
                elif s[i] == '"':
                    i += 1
                    break
                else:
                    buf.append(s[i])
                    i += 1
            toks.append(("str", "".join(buf)))
        elif c.isspace():
            i += 1
        else:
            buf = []
            while i < n and not s[i].isspace() and s[i] not in '()"':
                buf.append(s[i])
                i += 1
            toks.append(("atom", "".join(buf)))
    return toks


def _extract_envelope(raw_str: str) -> str | None:
    """Return the ENVELOPE S-expression from a FETCH response.

    IMAP sends 'ENVELOPE (' with a space (not '(ENVELOPE'), so split on the
    keyword, then balance parens respecting quoted strings.
    """
    idx = raw_str.find("ENVELOPE")
    if idx == -1:
        return None
    start = raw_str.find("(", idx)
    if start == -1:
        return None
    depth = 0
    in_q = False
    i = start
    while i < len(raw_str):
        c = raw_str[i]
        if in_q:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_q = False
        elif c == '"':
            in_q = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return raw_str[start:i + 1]
        i += 1
    return None


def _parse_sexpr(toks, i=0):
    """Parse one S-expression starting at toks[i] == '('. Returns (node, next_i).

    node is a list of children; leaves are ("str", v) / ("atom", v) tuples.
    """
    if i >= len(toks) or toks[i] != "(":
        return None, i
    i += 1
    items = []
    while i < len(toks) and toks[i] != ")":
        if toks[i] == "(":
            node, i = _parse_sexpr(toks, i)
            items.append(node)
        else:
            items.append(toks[i])
            i += 1
    return items, i + 1  # skip ')'


def _leaf(node) -> str:
    """String value of a leaf node; '' for NIL or a nested list."""
    if isinstance(node, tuple):
        val = node[1]
        return "" if val == "NIL" else val
    return ""


def _parse_env(s):
    """Parse an IMAP ENVELOPE S-expression into date/subject/sender.

    ENVELOPE field order: date, subject, from, sender, reply-to, to, cc, bcc,
    in-reply-to, message-id. `from` is (name adl mailbox host).
    """
    env = {}
    toks = _tokenize(s)
    node, _ = _parse_sexpr(toks, 0)
    if not node:
        return env
    if len(node) > 0:
        env["date"] = _leaf(node[0])
    if len(node) > 1:
        env["subject"] = _leaf(node[1])
    if len(node) > 2 and isinstance(node[2], list) and node[2]:
        # from = ( address* ) — a LIST of addresses; take the first.
        addr_node = node[2][0]
        if isinstance(addr_node, list):
            name = _leaf(addr_node[0]) if addr_node else ""
            mailbox = _leaf(addr_node[2]) if len(addr_node) > 2 else ""
            host = _leaf(addr_node[3]) if len(addr_node) > 3 else ""
            addr = f"{mailbox}@{host}" if mailbox and host else mailbox
            env["sender"] = f"{name} <{addr}>" if name else addr
    return env


def _extract_size(s):
    m = __import__("re").search(r"RFC822\.SIZE (\d+)", s)
    return int(m.group(1)) if m else 0


def _cfg():
    return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


def _save_cfg(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _cache_creds(label, **kw):
    cfg = _cfg()
    cfg["email"] = cfg.get("email", {})
    cfg["email"][label] = kw
    _save_cfg(cfg)


def _get_creds(label):
    return _cfg().get("email", {}).get(label, {})


def _imap_connect(host, port, user, passwd, use_ssl=True):
    if use_ssl:
        ctx = ssl.create_default_context()
        m = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
    else:
        m = imaplib.IMAP4(host, port)
        m.starttls(ssl_context=ssl.create_default_context())
    m.login(user, passwd)
    return m


def email_list(folder="INBOX", limit=10, label="default",
               imap_host=None, imap_port=993, imap_user=None, imap_pass=None):
    """List recent emails in a folder. Returns JSON with uid, from, subject, date, size."""
    c = _get_creds(label) if not imap_host else {}
    host = imap_host or c.get("imap_host")
    port = imap_port or c.get("imap_port", 993)
    user = imap_user or c.get("imap_user")
    pw = imap_pass or c.get("imap_pass")
    if not all([host, user, pw]):
        return {"error": "Missing IMAP credentials. Pass imap_host/imap_user/imap_pass or run email_configure first."}
    _cache_creds(label, imap_host=host, imap_port=port, imap_user=user, imap_pass=pw)
    try:
        m = _imap_connect(host, port, user, pw)
        m.select(f'"{folder}"')
        status, data = m.search(None, "ALL")
        uids = data[0].split()[-limit:] if data[0] else []
        out = []
        for uid in reversed(uids):
            uid_b = uid if isinstance(uid, bytes) else uid.encode()
            st, dt = m.fetch(uid_b, "(RFC822.SIZE ENVELOPE)")
            if st != "OK":
                continue
            raw = dt[0]
            raw_str = raw.decode() if isinstance(raw, bytes) else raw
            env_str = _extract_envelope(raw_str)
            if not env_str:
                continue
            env = _parse_env(env_str)
            out.append({
                "uid": uid.decode() if isinstance(uid, bytes) else uid,
                "from": env.get("sender", ""),
                "subject": env.get("subject", ""),
                "date": env.get("date", ""),
                "size": _extract_size(raw_str),
            })
        m.logout()
        return {"folder": folder, "count": len(out), "emails": out}
    except Exception as e:
        return {"error": str(e)}


def email_read(uid, folder="INBOX", label="default",
               imap_host=None, imap_port=993, imap_user=None, imap_pass=None):
    """Read a single email by UID. Returns from/subject/date/body."""
    c = _get_creds(label) if not imap_host else {}
    host = imap_host or c.get("imap_host")
    port = imap_port or c.get("imap_port", 993)
    user = imap_user or c.get("imap_user")
    pw = imap_pass or c.get("imap_pass")
    if not all([host, user, pw]):
        return {"error": "Missing IMAP credentials."}
    try:
        m = _imap_connect(host, port, user, pw)
        m.select(f'"{folder}"')
        st, dt = m.fetch(uid.encode() if isinstance(uid, str) else uid, "(RFC822)")
        if st != "OK":
            return {"error": f"UID {uid} not found"}
        msg = message_from_bytes(dt[0][1])
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="replace")
        return {
            "uid": str(uid),
            "from": msg["From"],
            "to": msg["To"],
            "subject": msg["Subject"],
            "date": msg["Date"],
            "body": body[:3000],
        }
    except Exception as e:
        return {"error": str(e)}


def _smtp_host_for(imap_host: str) -> str:
    """Derive an SMTP host from an IMAP host.

    IMAP and SMTP live on different hostnames (imap.gmail.com vs
    smtp.gmail.com), so reusing the IMAP host fails TLS hostname checks.
    """
    h = (imap_host or "").strip()
    if h.startswith("imap."):
        return "smtp." + h[5:]
    return h


def email_send(to, subject, body, cc=None, bcc=None, label="default",
               smtp_host=None, smtp_port=587, smtp_user=None, smtp_pass=None,
               imap_host=None, imap_port=993, imap_user=None, imap_pass=None):
    """Send an email. Caches SMTP + IMAP creds under the same label."""
    c = _get_creds(label) if not smtp_host else {}
    shost = smtp_host or c.get("smtp_host") or _smtp_host_for(c.get("imap_host"))
    sport = smtp_port or c.get("smtp_port", 587)
    suser = smtp_user or c.get("smtp_user") or c.get("imap_user")
    spass = smtp_pass or c.get("smtp_pass") or c.get("imap_pass")
    if not all([shost, suser, spass, to, subject]):
        return {"error": "Missing SMTP credentials or recipients. Pass smtp_host/smtp_user/smtp_pass + to/subject/body."}
    _cache_creds(label, smtp_host=shost, smtp_port=sport, smtp_user=suser, smtp_pass=spass,
                 imap_host=imap_host or c.get("imap_host"), imap_port=imap_port or c.get("imap_port", 993),
                 imap_user=imap_user or c.get("imap_user"), imap_pass=imap_pass or c.get("imap_pass"))
    try:
        msg = MIMEMultipart()
        msg["From"] = suser
        msg["To"] = to
        msg["Cc"] = cc or ""
        msg["Bcc"] = bcc or ""
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg.attach(MIMEText(body, "plain"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(shost, sport) as s:
            s.starttls(context=ctx)
            s.login(suser, spass)
            s.sendmail(suser, [to] + ([cc] if cc else []) + ([bcc] if bcc else []), msg.as_string())
        return {"sent": True, "to": to, "subject": subject}
    except Exception as e:
        return {"error": str(e)}


def email_search(folder="INBOX", query="", limit=10, label="default",
                 imap_host=None, imap_port=993, imap_user=None, imap_pass=None):
    """Search emails by IMAP criteria (e.g. 'FROM alice', 'SUBJECT report')."""
    c = _get_creds(label) if not imap_host else {}
    host = imap_host or c.get("imap_host")
    port = imap_port or c.get("imap_port", 993)
    user = imap_user or c.get("imap_user")
    pw = imap_pass or c.get("imap_pass")
    if not all([host, user, pw]):
        return {"error": "Missing IMAP credentials."}
    try:
        m = _imap_connect(host, port, user, pw)
        m.select(f'"{folder}"')
        criteria = query or "ALL"
        st, data = m.search(None, criteria)
        uids = data[0].split()[-limit:] if data[0] else []
        out = [{"uid": u.decode()} for u in reversed(uids)]
        m.logout()
        return {"folder": folder, "query": criteria, "count": len(out), "emails": out}
    except Exception as e:
        return {"error": str(e)}


# --- register ---
register("email_list", {
    "name": "email_list",
    "description": "List recent emails in a folder. Returns uid/from/subject/date.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "IMAP folder", "default": "INBOX"},
            "limit": {"type": "integer", "description": "Max emails", "default": 10},
            "label": {"type": "string", "description": "Credential label", "default": "default"},
            "imap_host": {"type": "string", "description": "IMAP host (overrides cached)"},
            "imap_port": {"type": "integer", "description": "IMAP port", "default": 993},
            "imap_user": {"type": "string", "description": "IMAP username"},
            "imap_pass": {"type": "string", "description": "IMAP password"},
        },
        "required": [],
    },
}, email_list)

register("email_read", {
    "name": "email_read",
    "description": "Read a single email by UID. Returns from/subject/body.",
    "parameters": {
        "type": "object",
        "properties": {
            "uid": {"type": "string", "description": "Message UID"},
            "folder": {"type": "string", "default": "INBOX"},
            "label": {"type": "string", "default": "default"},
            "imap_host": {"type": "string"},
            "imap_port": {"type": "integer", "default": 993},
            "imap_user": {"type": "string"},
            "imap_pass": {"type": "string"},
        },
        "required": ["uid"],
    },
}, email_read)

register("email_send", {
    "name": "email_send",
    "description": "Send an email via SMTP. Caches credentials for future calls.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"},
            "label": {"type": "string", "default": "default"},
            "smtp_host": {"type": "string", "description": "SMTP host"},
            "smtp_port": {"type": "integer", "default": 587},
            "smtp_user": {"type": "string"},
            "smtp_pass": {"type": "string"},
            "imap_host": {"type": "string"},
            "imap_port": {"type": "integer", "default": 993},
            "imap_user": {"type": "string"},
            "imap_pass": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
    },
}, email_send)

register("email_search", {
    "name": "email_search",
    "description": "Search emails by IMAP criteria (FROM, SUBJECT, etc).",
    "parameters": {
        "type": "object",
        "properties": {
            "folder": {"type": "string", "default": "INBOX"},
            "query": {"type": "string", "description": "IMAP search crit e.g. FROM x, SUBJECT y"},
            "limit": {"type": "integer", "default": 10},
            "label": {"type": "string", "default": "default"},
            "imap_host": {"type": "string"},
            "imap_port": {"type": "integer", "default": 993},
            "imap_user": {"type": "string"},
            "imap_pass": {"type": "string"},
        },
        "required": [],
    },
}, email_search)