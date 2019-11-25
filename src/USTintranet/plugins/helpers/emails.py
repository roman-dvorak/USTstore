import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(message, options):
    s = smtplib.SMTP(host=options["email_smtp_host"], port=options["email_smtp_port"])
    s.starttls()
    s.login(options["email_address"], options["email_password"])
    s.send_message(message)


def generate_validation_message(address, token, options):
    msg = MIMEMultipart()

    msg["From"] = options["email_address"]
    msg["To"] = address
    msg["Subject"] = "Ověřovací email"

    msg.attach(MIMEText(f"Test email, token: {token}", "plain"))

    return msg


def generate_validation_token():
    return secrets.token_urlsafe(64)
