#!/usr/bin/env python3
"""
app.py — Email Sender as a hosted web app.

A single-file Flask application: an HTML form in the browser controls every
element of the email (sender display name, recipients, date, subject, body,
priority, attachments, SMTP settings). The backend builds the MIME message and
sends it via your own SMTP account.

Run locally:      python3 app.py            -> http://localhost:8000
Deploy (Render):  see README.md             -> https://<your-app>.onrender.com
"""

import os
import smtplib
import ssl
from datetime import datetime, timezone

from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from flask import Flask, render_template_string, request
import mimetypes

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload cap

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Email Sender</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background: #f3f4f6; margin: 0; padding: 24px; color: #111827; }
  main { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  .sub { color: #6b7280; font-size: .85rem; margin-bottom: 20px; }
  fieldset { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
             padding: 16px 18px; margin: 0 0 16px; }
  legend { font-weight: 600; font-size: .85rem; padding: 0 6px; color: #374151; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
  label { display: block; font-size: .78rem; color: #4b5563; margin-bottom: 3px; }
  input[type=text], input[type=email], input[type=password], input[type=number],
  textarea, select {
    width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 8px;
    font: inherit; font-size: .9rem; background: #fff; }
  textarea { resize: vertical; }
  .full { grid-column: 1 / -1; }
  .hint { font-size: .72rem; color: #9ca3af; margin-top: 3px; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  button, .btn { background: #2563eb; color: #fff; border: 0; border-radius: 8px;
    padding: 10px 18px; font: inherit; font-weight: 600; cursor: pointer; }
  button.secondary { background: #fff; color: #2563eb; border: 1px solid #2563eb; }
  button:hover { filter: brightness(1.08); }
  .flash { border-radius: 10px; padding: 12px 14px; margin-bottom: 16px;
           font-size: .88rem; white-space: pre-wrap; }
  .ok  { background: #ecfdf5; border: 1px solid #6ee7b7; color: #065f46; }
  .err { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
  .warn { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
  details { font-size: .8rem; color: #6b7280; }
  pre { background: #111827; color: #d1d5db; padding: 12px; border-radius: 8px;
        overflow: auto; font-size: .75rem; max-height: 320px; }
  .check { display: flex; gap: 6px; align-items: center; margin-top: 6px; }
  .check label { margin: 0; }
</style>
</head>
<body>
<main>
  <h1>✉️ Email Sender</h1>
  <div class="sub">Fill the form, send through your own SMTP account. Nothing is stored.</div>

  {% if flash %}
  <div class="flash {{ flash_class }}">{{ flash }}</div>
  {% endif %}

  <form method="post" action="/send" enctype="multipart/form-data">
    <fieldset>
      <legend>Message</legend>
      <div class="grid">
        <div><label>Sender name</label>
          <input type="text" name="from_name" value="{{ v.from_name }}" placeholder="Acme Support"></div>
        <div><label>Sender email (must match SMTP login)</label>
          <input type="email" name="from_email" value="{{ v.from_email }}" required></div>
        <div class="full"><label>To (comma-separated)</label>
          <input type="text" name="to" value="{{ v.to }}" required placeholder="alice@example.com, bob@example.com"></div>
        <div><label>Cc</label><input type="text" name="cc" value="{{ v.cc }}"></div>
        <div><label>Bcc</label><input type="text" name="bcc" value="{{ v.bcc }}"></div>
        <div><label>Reply-To</label><input type="text" name="reply_to" value="{{ v.reply_to }}"></div>
        <div><label>Priority</label>
          <select name="priority">
            <option value="normal" {{ 'selected' if v.priority=='normal' }}>normal</option>
            <option value="high" {{ 'selected' if v.priority=='high' }}>high</option>
            <option value="low" {{ 'selected' if v.priority=='low' }}>low</option>
          </select></div>
        <div class="full"><label>Subject</label>
          <input type="text" name="subject" value="{{ v.subject }}" required></div>
        <div><label>Date (optional)</label>
          <input type="text" name="date" value="{{ v.date }}" placeholder="2026-10-04T09:30:00+03:00">
          <div class="hint">ISO-8601 with timezone. Blank = now.</div></div>
        <div><label>Attachments</label>
          <input type="file" name="attachments" multiple></div>
        <div class="full"><label>Body</label>
          <textarea name="body" rows="7">{{ v.body }}</textarea>
          <div class="check"><input type="checkbox" id="ishtml" name="is_html" {{ 'checked' if v.is_html }}>
            <label for="ishtml">Body is HTML</label></div></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>SMTP server</legend>
      <div class="grid">
        <div><label>Host</label><input type="text" name="smtp_host" value="{{ v.smtp_host }}" required></div>
        <div><label>Port</label><input type="number" name="smtp_port" value="{{ v.smtp_port }}" required></div>
        <div><label>Username</label><input type="text" name="smtp_user" value="{{ v.smtp_user }}" required></div>
        <div><label>Password / app password</label>
          <input type="password" name="smtp_pass" value="{{ v.smtp_pass }}" required></div>
        <div><label>Security</label>
          <select name="smtp_security">
            <option value="starttls" {{ 'selected' if v.smtp_security=='starttls' }}>STARTTLS (port 587)</option>
            <option value="ssl" {{ 'selected' if v.smtp_security=='ssl' }}>SSL (port 465)</option>
          </select></div>
      </div>
      <div class="hint">Gmail: smtp.gmail.com, 587, STARTTLS, and an App Password
        (Google Account → Security → App Passwords; needs 2-Step Verification).</div>
    </fieldset>

    <div class="row">
      <button type="submit">Send email</button>
      <button type="submit" class="secondary" formaction="/preview">Preview message</button>
    </div>
  </form>

  {% if preview %}
  <details open style="margin-top:16px">
    <summary>Raw MIME message (this is what would be sent)</summary>
    <pre>{{ preview }}</pre>
  </details>
  {% endif %}
</main>
</body>
</html>"""


def defaults():
    return {
        "from_name": "", "from_email": os.environ.get("SMTP_USER", ""),
        "to": "", "cc": "", "bcc": "", "reply_to": "", "subject": "",
        "date": "", "priority": "normal", "body": "", "is_html": False,
        "smtp_host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_user": os.environ.get("SMTP_USER", ""),
        "smtp_pass": os.environ.get("SMTP_PASS", ""),
        "smtp_security": os.environ.get("SMTP_SECURITY", "starttls"),
    }


def split_addrs(raw):
    return [a.strip() for a in (raw or "").replace(";", ",").split(",") if a.strip()]


def build_message(form, files):
    to = split_addrs(form.get("to"))
    if not to:
        raise ValueError("At least one To recipient is required.")
    from_email = (form.get("from_email") or "").strip()
    if not from_email:
        raise ValueError("Sender email is required.")
    if not (form.get("subject") or "").strip():
        raise ValueError("Subject is required.")

    msg = EmailMessage()
    name = (form.get("from_name") or "").strip()
    msg["From"] = f"{name} <{from_email}>" if name else from_email
    msg["To"] = ", ".join(to)
    cc, bcc = split_addrs(form.get("cc")), split_addrs(form.get("bcc"))
    if cc:
        msg["Cc"] = ", ".join(cc)
    if (form.get("reply_to") or "").strip():
        msg["Reply-To"] = form["reply_to"].strip()
    msg["Subject"] = form["subject"].strip()

    raw_date = (form.get("date") or "").strip()
    if raw_date:
        dt = datetime.fromisoformat(raw_date)  # ValueError if malformed
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        msg["Date"] = format_datetime(dt)
    else:
        msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid()

    prio = form.get("priority", "normal")
    if prio == "high":
        msg["X-Priority"], msg["Importance"] = "1", "High"
    elif prio == "low":
        msg["X-Priority"], msg["Importance"] = "5", "Low"

    body = form.get("body") or ""
    if form.get("is_html"):
        msg.set_content("This message contains HTML content. "
                        "Please view it in an HTML-capable email client.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    for f in files.getlist("attachments"):
        if not f or not f.filename:
            continue
        ctype, _ = mimetypes.guess_type(f.filename)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        data = f.read()
        if data:
            msg.add_attachment(data, maintype=maintype, subtype=subtype,
                               filename=os.path.basename(f.filename))
    return msg, to + cc + bcc


def send_message(msg, recipients, form):
    host = (form.get("smtp_host") or "").strip()
    user = (form.get("smtp_user") or "").strip()
    password = form.get("smtp_pass") or ""
    port = int((form.get("smtp_port") or "587").strip())
    security = form.get("smtp_security", "starttls")
    if not (host and user and password):
        raise ValueError("SMTP host, username and password are required.")

    context = ssl.create_default_context()
    if security == "ssl":
        server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=context)
    try:
        server.login(user, password)
        return server.send_message(msg, to_addrs=recipients)  # {} on success
    finally:
        server.quit()


def collect_form(form):
    v = defaults()
    for key in v:
        if key == "is_html":
            v[key] = bool(form.get("is_html"))
        elif key in form:
            v[key] = form.get(key, v[key])
    return v


@app.get("/")
def index():
    return render_template_string(PAGE, v=defaults(), flash=None, preview=None)


@app.post("/preview")
def preview():
    v = collect_form(request.form)
    try:
        msg, _ = build_message(request.form, request.files)
        return render_template_string(PAGE, v=v, flash=None,
                                      preview=msg.as_string())
    except Exception as e:
        return render_template_string(PAGE, v=v, preview=None,
                                      flash=f"Cannot build message: {e}",
                                      flash_class="err")


@app.post("/send")
def send():
    v = collect_form(request.form)
    try:
        msg, recipients = build_message(request.form, request.files)
        refused = send_message(msg, recipients, request.form)
        if refused:
            flash, cls = f"Sent, but some recipients were refused: {refused}", "warn"
        else:
            flash, cls = f"Sent to {', '.join(recipients)}", "ok"
    except smtplib.SMTPAuthenticationError:
        flash, cls = ("Authentication failed. Check the username/password — "
                      "Gmail requires an App Password, not your login password."), "err"
    except Exception as e:
        flash, cls = f"Error: {type(e).__name__}: {e}", "err"
    return render_template_string(PAGE, v=v, flash=flash, flash_class=cls,
                                  preview=None)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
