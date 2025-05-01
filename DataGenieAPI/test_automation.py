import requests
import json
import time
import pandas as pd
import subprocess
import matplotlib
from tabulate import tabulate
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from db_connection import get_db_connection
from logger_config import logger  # Import centralized logger
import logging

# File Paths
TEMPLATE_PATH = r"C:\\Products\\CTRMA\\CTRMA_NEW\\CTRMAMETRICS\\DataGenieAPI\\test_report_template.html"
RESULTS_PATH = r"C:\Products\CTRMA\CTRMA_NEW\CTRMAMETRICS\TestResults\test_results.html"
TEST_CASES_PATH = r"C:\\Products\\CTRMA\\CTRMA_NEW\\CTRMAMETRICS\\DataGenieAPI\\final_test_cases.json"
# TEST_CASES_PATH = r"C:\\Products\\CTRMA\\CTRMA_NEW\\CTRMAMETRICS\\DataGenieAPI\\test_cases.json"

# New Endpoint
GEN_EXEC_URL = "http://127.0.0.1:8000/generate-and-execute-sql"

# Load Test Cases
with open(TEST_CASES_PATH, "r") as json_file:
    test_cases = json.load(json_file)["test_cases"]

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set the level to INFO or DEBUG as needed
# Store Results
results = []
pass_count = 0
fail_count = 0
complexity_levels = {"Low": 0, "Medium": 0, "High": 0, "Very High": 0}

for index, query in enumerate(test_cases):
    print(f"Running Test Case {index+1}/{len(test_cases)}: {query}")

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
    # logging.info(f"exec_result   --->: {exec_result}")
    
    exec_msg = exec_result.get("message", "Unknown")
    exec_code = exec_result.get("message_code", 500)
    # logging.info(f"message_code   --->: {exec_result.get("message_code", 500)}")
    # logging.info(f"exec_code   --->: {exec_code}")
    exec_time = exec_result.get("execution_time", "N/A")
    validation_flag = data.get("validation_flag", False)
    recommendations = data.get("generated_recommendations", [])
    # logging.info(f"recommendations   --->: {recommendations}")

    if complexity in complexity_levels:
        complexity_levels[complexity] += 1

    if validation_flag:
        pass_count += 1
        status = "PASS"
        # reason = f"Execution restricted due to validation warnings: {', '.join(recommendations)}"
        reason = recommendations
    elif exec_code in [200,204,400]:
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

# Save DataFrame
df = pd.DataFrame(results)

# Save HTML Report
with open(TEMPLATE_PATH, "r", encoding="utf-8") as tpl:
    html_template = tpl.read()

html_filled = html_template.replace("{total_cases}", str(len(results)))\
    .replace("{pass_count}", str(pass_count))\
    .replace("{fail_count}", str(fail_count))\
    .replace("{low_count}", str(complexity_levels["Low"]))\
    .replace("{medium_count}", str(complexity_levels["Medium"]))\
    .replace("{high_count}", str(complexity_levels["High"]))\
    .replace("{very_high_count}", str(complexity_levels["Very High"]))\
    .replace("{html_output}", df.to_html(index=False, classes="table table-hover", escape=False))\
    .replace("{test_results_chart}", "cid:test_results_chart")\
    .replace("{complexity_chart}", "cid:complexity_chart")

with open(RESULTS_PATH, "w", encoding="utf-8") as f:
    f.write(html_filled)

# Generate charts
CHART_DIR = r"C:\\Products\\Innovations\\DataGenie\\TestResults\\"

plt.figure(figsize=(4, 4))
plt.pie([pass_count, fail_count], labels=["Passed", "Failed"], autopct="%1.1f%%", colors=["#28a745", "#dc3545"])
plt.title("Test Case Results Summary")
plt.axis("equal")
plt.savefig(CHART_DIR + "test_results_chart.png", dpi=100, bbox_inches='tight')
plt.close()

plt.figure(figsize=(4.5, 3))
plt.bar(complexity_levels.keys(), complexity_levels.values(), color=["#17a2b8", "#ffc107", "#fd7e14", "#dc3545"])
plt.title("Complexity Level Distribution")
plt.xlabel("Complexity Level")
plt.ylabel("Test Cases")
plt.savefig(CHART_DIR + "complexity_chart.png", dpi=100, bbox_inches='tight')
plt.close()

print("\n📊 Test Execution Summary:\n")
print(tabulate(
    df[["Test Case", "Query", "Generation Time", "Execution Time", "Status"]],
    headers="keys",
    tablefmt="fancy_grid",
    showindex=False
))

print(f"Test report saved to {RESULTS_PATH}")
subprocess.run(["python", "sendhtmlreport.py"])