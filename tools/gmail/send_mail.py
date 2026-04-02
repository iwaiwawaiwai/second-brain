#!/usr/bin/env python3
"""
Gmail メール送信ツール（SMTP）

使い方:
  python send_mail.py --to "xxx@example.com" --subject "件名" --body "本文"
  python send_mail.py --to "xxx@example.com" --subject "件名" --file body.txt
"""

import argparse
import smtplib
from email.mime.text import MIMEText
from pathlib import Path


TOOLS_DIR = Path(__file__).parent


def load_env() -> dict:
    env = {}
    for line in (TOOLS_DIR / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def send(to: str, subject: str, body: str, cc: str = None):
    env = load_env()
    address      = env["GMAIL_ADDRESS"]
    app_password = env["GMAIL_APP_PASSWORD"].replace(" ", "")

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"]    = address
    msg["To"]      = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(address, app_password)
        recipients = [to] + ([cc] if cc else [])
        smtp.sendmail(address, recipients, msg.as_bytes())

    print(f"[sent] → {to}")
    if cc:
        print(f"[sent] CC: {cc}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to",      required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body",    default=None)
    parser.add_argument("--file",    default=None, help="本文をファイルから読み込む")
    parser.add_argument("--cc",      default=None)
    args = parser.parse_args()

    if args.file:
        body = Path(args.file).read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        print("--body または --file を指定してください")
        return

    send(args.to, args.subject, body, args.cc)


if __name__ == "__main__":
    main()
