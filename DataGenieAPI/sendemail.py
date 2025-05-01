import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser

# # Load configuration from config.inf
config = configparser.ConfigParser()
config.read("config.inf")

SMTP_SERVER = config.get("SMTP", "SERVER")
SMTP_PORT = config.getint("SMTP", "PORT")
SMTP_USER = config.get("SMTP", "USER")
SMTP_PASSWORD = config.get("SMTP", "PASSWORD")


TO_EMAILS = ["abhagat@ViaPlus.com", "asiripuram@ViaPlus.com", "skunchavarapu@Viaplus.com", "vchindukuru@viaplus.com","lnarahari@viaplus.com","snukala@viaplus.com"]
FROM_EMAIL = SMTP_USER
SUBJECT = "Data Genie - Execution Failure - Ticket Notification"

def send_error_email(ticket_number, prompt, generated_sql, summary, audit_id, error):
    # ✅ Professional HTML content with placeholders for Ticket Details
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Data Genie - Execution Failure Ticket Notification</title>
        <style>
            body {{
                background-color: #f4f6f9;
                font-family: 'Poppins', sans-serif;
            }}
            .container {{
                margin: 40px auto;
                width: 90%;
                max-width: 900px;
            }}
            h2 {{
                font-weight: bold;
                text-transform: capitalize;
                text-align: center;
                margin-bottom: 30px;
                color: #333;
            }}
            .panel {{
                background: #fff;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
            }}
            .table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 16px;
            }}
            .table th {{
                background-color: #6c8ebf;
                color: #fff;
                padding: 14px;
                text-align: left;
                font-size: 17px;
            }}
            .table td {{
                background-color: #ffffff;
                padding: 14px;
                color: #333;
            }}
            .table tr:nth-child(even) td {{
                background-color: #f2f5fa;
            }}
            .table tr:hover td {{
                background-color: #eaf0f6;
            }}
        </style>
    </head>

    <body>
        <div class="container">
            <h2>🚨 Data Genie - Execution Failure Notification</h2>

            <div class="panel">
                <h4>🎟 Ticket Details (Auto-Generated)</h4>
                <table class="table">
                    <tr><th>Ticket Number</th><td><b>{ticket_number}</b></td></tr>
                    <tr><th>Audit ID</th><td><b>{audit_id}</b></td></tr>
                    <tr><th>Assigned To</th><td><b>Avishek</b></td></tr>
                    <tr><th>Error</th><td><b>{error}</b></td></tr>
                </table>
            </div>

            <div class="panel">
                <h4>📝 Execution Details</h4>
                <table class="table">
                    <tr><th>Prompt</th><td>{prompt}</td></tr>
                    <tr><th>Generated SQL</th><td>{generated_sql}</td></tr>
                    <tr><th>Summary</th><td>{summary}</td></tr>                
                </table>
            </div>
            <p style="text-align:center;"><b>Regards,<br>Data Genie Monitoring Bot</b></p>
        </div>
    </body>
    </html>
    """

    # ✅ Create the Email
    msg = MIMEMultipart("related")
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(html_content, "html"))

    # ✅ Send the email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAILS, msg.as_string())
        server.quit()
        print("✅ Execution failure email sent successfully.")
    except Exception as e:
        print(f"❌ Error sending email: {e}")