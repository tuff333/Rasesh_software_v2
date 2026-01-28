import smtplib
import ssl
from email.message import EmailMessage
from app.services.settings import load_settings


def send_invoice_email(to_email, subject, body, pdf_path, vendor_name=None):
    """
    Sends an invoice email with PDF attachment.
    Returns (True, None) on success, (False, error_message) on failure.
    """

    settings = load_settings()

    smtp_host = settings.get("smtp_host", "")
    smtp_port = int(settings.get("smtp_port", 587))
    smtp_username = settings.get("smtp_username", "")
    smtp_password = settings.get("smtp_password", "")
    smtp_from = settings.get("smtp_from", "")

    if not smtp_host or not smtp_from:
        return False, "SMTP settings are incomplete. Please configure them in Settings."

    # Build email
    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject

    # Body
    if vendor_name:
        body = f"Vendor: {vendor_name}\n\n" + body

    msg.set_content(body or "Please find your invoice attached.")

    # Attach PDF
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        msg.add_attachment(
            pdf_data,
            maintype="application",
            subtype="pdf",
            filename=pdf_path.split("/")[-1]
        )
    except Exception as e:
        return False, f"Failed to attach PDF: {e}"

    # Send email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=context)
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(msg)

        return True, None

    except Exception as e:
        return False, str(e)
