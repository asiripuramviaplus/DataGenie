import smtplib
import os
import configparser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# Load configuration
config = configparser.ConfigParser()
config.read('config.inf')

# SMTP Configuration
SMTP_SERVER = config.get('SMTP', 'SERVER')
SMTP_PORT = config.getint('SMTP', 'PORT')
SMTP_USER = config.get('SMTP', 'USER')
SMTP_PASSWORD = config.get('SMTP', 'PASSWORD')

# Email Details
TO_EMAILS = config.get('EMAIL', 'TO_EMAILS').split(',')
CC_EMAILS = config.get('EMAIL', 'CC_EMAILS').split(',')
FROM_EMAIL = SMTP_USER
SUBJECT = "Data Genie - Talk to Data - Automated Test Report"

# Paths to generated report and images
RESULTS_PATH = r"C:\Products\CTRMA\CTRMA_NEW\CTRMAMETRICS\TestResults\test_results.html"
TEST_RESULTS_CHART = r"C:\Products\CTRMA\CTRMA_NEW\CTRMAMETRICS\TestResults\test_results_chart.png"
COMPLEXITY_CHART = r"C:\Products\CTRMA\CTRMA_NEW\CTRMAMETRICS\TestResults\complexity_chart.png"

# Ensure HTML report exists
if not os.path.exists(RESULTS_PATH):
    print("Error: Test report file not found.")
    exit(1)

# Read the already generated HTML report
with open(RESULTS_PATH, "r", encoding="utf-8") as file:
    html_content = file.read()

# Ensure the placeholders for images exist in the HTML report
html_content = html_content.replace("{test_results_chart}", "cid:test_results_chart")\
                           .replace("{complexity_chart}", "cid:complexity_chart")

# Function to attach images inline
def attach_image(msg, img_path, cid_name):
    if os.path.exists(img_path):
        with open(img_path, "rb") as img:
            img_data = MIMEImage(img.read())
            img_data.add_header("Content-ID", f"<{cid_name}>")
            img_data.add_header("Content-Disposition", "inline", filename=os.path.basename(img_path))  # Fixed typo
            msg.attach(img_data)
    else:
        print(f"Warning: {os.path.basename(img_path)} not found!")

# Create Email Message
msg = MIMEMultipart("related")
msg["From"] = FROM_EMAIL
msg["To"] = ", ".join(TO_EMAILS)  # Convert list to comma-separated string
msg["Cc"] = ", ".join(CC_EMAILS)  # Convert list to string for CC
msg["Subject"] = SUBJECT

# Attach HTML Content
msg.attach(MIMEText(html_content, "html"))

# Attach inline images
attach_image(msg, TEST_RESULTS_CHART, "test_results_chart")
attach_image(msg, COMPLEXITY_CHART, "complexity_chart")

# Send the email
try:
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    server.sendmail(FROM_EMAIL, TO_EMAILS + CC_EMAILS, msg.as_string())  # Include CC recipients
    server.quit()
    print("✅ Test report sent successfully with multiple recipients and CC.")
except Exception as e:
    print(f"❌ Error sending email: {e}")