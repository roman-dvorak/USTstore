import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(message, options):
    s = smtplib.SMTP(host=options["email_smtp_host"], port=options["email_smtp_port"])
    s.starttls()
    s.login(options["email_address"], options["email_password"])
    s.send_message(message)


def generate_validation_message(address, user_id, token, options):
    link = f"{options['intranet_url']}/users/api/u/{user_id}/validateemail/{token}"

    msg = MIMEMultipart("alternative")

    msg["From"] = options["email_address"]
    msg["To"] = address
    msg["Subject"] = "Ověřovací email"

    plain_text = MIMEText(
        "Dobrý den,\n"
        "pro ověření vašeho emailu v systému "
        + options['intranet_name'] +
        " prosím navštivte následující odkaz:\n"
        + link +
        "\n"
        "S přáním hezkého dne\n"
        + options['intranet_name'] +
        "\n",
        "plain"
    )

    html_text = MIMEText(
        f"""
        <html>
            <body>
                <p>
                    <b>Dobrý den,</b><br>
                    pro ověření vašeho emailu v systému {options['intranet_name']} prosím klikněte 
                    na následující odkaz:
                </p>
                <p>
                    <a href="{link}">{link}</a>
                </p>
                <p>
                    S přáním hezkého dne<br>
                    {options['intranet_name']}
                </p>
            </body>
        </html>
        """,
        "html"
    )

    msg.attach(plain_text)
    msg.attach(html_text)

    return msg


def generate_validation_token():
    return secrets.token_urlsafe(64)
