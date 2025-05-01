import requests
import json
import time
import pandas as pd
from tabulate import tabulate
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser

# Load configuration
config = configparser.ConfigParser()
config.read('config.inf')

SMTP_SERVER = config.get('SMTP', 'SERVER')
SMTP_PORT = config.getint('SMTP', 'PORT')
SMTP_USER = config.get('SMTP', 'USER')
SMTP_PASSWORD = config.get('SMTP', 'PASSWORD')
EMAIL_RECIPIENTS = config.get('EMAIL', 'RECIPIENTS').split(',')

# Endpoint and Test Cases
GEN_EXEC_URL = "http://127.0.0.1:8000/generate-and-execute-sql"
TEST_CASES_PATH = "final_test_cases.json"

# Load Test Cases
with open(TEST_CASES_PATH, "r") as json_file:
    test_cases = json.load(json_file)["test_cases"]

# Execute Test Cases
results = []
pass_count = 0
fail_count = 0
complexity_levels = {"Low": 0, "Medium": 0, "High": 0, "Very High": 0}

for index, query in enumerate(test_cases):
    print(f"Running Test Case {index + 1}/{len(test_cases)}: {query}")
    payload = {"query": query}
    start_time = time.time()
    response = requests.post(GEN_EXEC_URL, json=payload)
    time_taken = time.time() - start_time

    if response.status_code != 200:
        fail_count += 1
        results.append({
            "Test Case": index + 1, "Query": query, "Generated SQL": "ERROR",
            "Complexity Level": "N/A", "Generation Time": "N/A",
            "Execution Time": "N/A", "Status": "FAIL", "Reason": "API Error"
        })
        continue

    data = response.json()
    gen_sql = data.get("generated_sql", "N/A")
    raw_complexity = data.get("query_complexity", {})
    if isinstance(raw_complexity, str):
        try:
            raw_complexity = json.loads(raw_complexity)
        except json.JSONDecodeError:
            raw_complexity = {}

    complexity = raw_complexity.get("complexity_level", "N/A")
    exec_result = data.get("execution_result", {})
    exec_msg = exec_result.get("message", "Unknown")
    exec_code = exec_result.get("message_code", 500)
    exec_time = exec_result.get("execution_time", "N/A")
    validation_flag = data.get("validation_flag", False)
    recommendations = data.get("generated_recommendations", [])

    if complexity in complexity_levels:
        complexity_levels[complexity] += 1

    if validation_flag or exec_code in [200, 204, 400]:
        pass_count += 1
        status = "PASS"
        reason = recommendations
    else:
        fail_count += 1
        status = "FAIL"
        reason = exec_msg

    results.append({
        "Test Case": index + 1, "Query": query, "Generated SQL": gen_sql,
        "Complexity Level": complexity, "Generation Time": f"{time_taken:.2f} sec",
        "Execution Time": exec_time, "Status": status, "Reason": reason
    })

# Convert to DataFrame
df = pd.DataFrame(results)

# HTML Report Template (Inline Styling for Email)
html_table = df.to_html(index=False, classes="styled-table", escape=False)

html_body = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        h2 {{
            color: #2c3e50;
        }}
        .summary {{
            background-color: #ffffff;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .styled-table {{
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 14px;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
        }}
        .styled-table th, .styled-table td {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        .styled-table th {{
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }}
        .styled-table tr:nth-child(even) {{ background-color: #f3f3f3; }}
        .styled-table tr:hover {{ background-color: #ddd; }}
    </style>
</head>
<body>
    <h2>🧪 Test Report - DataGenie</h2>
    <div class="summary">
        <p><strong>Total Test Cases:</strong> {len(results)}</p>
        <p><strong>✅ Passed:</strong> {pass_count}</p>
        <p><strong>❌ Failed:</strong> {fail_count}</p>
        <p><strong>Complexity Breakdown:</strong></p>
        <ul>
            <li>Low: {complexity_levels["Low"]}</li>
            <li>Medium: {complexity_levels["Medium"]}</li>
            <li>High: {complexity_levels["High"]}</li>
            <li>Very High: {complexity_levels["Very High"]}</li>
        </ul>
    </div>
    {html_table}
</body>
</html>
"""

# Load table details from schema_template.json
SCHEMA_FILE_PATH = "schema_template.json"

def load_table_details(schema_file_path):
    with open(schema_file_path, "r", encoding="utf-8") as file:  # Specify UTF-8 encoding
        schema_data = json.load(file)
    return schema_data

def generate_table_details_html(schema_data):
    html_content = "<h3>📋 Database: CTRMA_20181001</h3><ul>"
    for table_name, table_info in schema_data.items():
        description = table_info.get("Description", "No description available.")
        html_content += f"""
        <li>
            <strong>Table:</strong> {table_name}<br>
            <strong>Description:</strong> {description}
        </li>
        """
    html_content += "</ul>"
    return html_content

# Load schema data
schema_data = load_table_details(SCHEMA_FILE_PATH)

# Generate dynamic table details HTML
table_details_html = generate_table_details_html(schema_data)

# Append table details to the HTML body
html_body += table_details_html

# Email Sender Function
def send_email_report(subject, html_content):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(EMAIL_RECIPIENTS)
    msg['Subject'] = subject

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, EMAIL_RECIPIENTS, msg.as_string())
        server.quit()
        print("✅ Email report sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# Send the report
send_email_report("🧪 DataGenie Test Report", html_body)
