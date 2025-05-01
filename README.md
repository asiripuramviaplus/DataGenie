# Data Genie – AI-Powered NLP to SQL Query Tool for Mobility Platform

## 🔍 Introduction
Data Genie is an AI-powered tool designed for the **Mobility Platform** to translate natural language statements into valid, secure, and optimized SQL Server queries. It leverages **Azure OpenAI GPT-4o**, a schema-aware instruction layer, and strong validation mechanisms to empower users with seamless, intuitive access to data.

## ✨ Key Features
- Translates natural language queries into optimized SQL Server syntax.
- Utilizes Azure OpenAI GPT-4o for intent understanding and query generation.
- Performs content and SQL safety checks (PII, destructive ops).
- Dynamically maps queries to schema metadata.
- Caches previous prompt-to-SQL mappings for reusability.
- Logs all prompts, SQL, summaries, and execution metrics.
- Triggers alert emails for execution failures.
- Automatically generates monthly dashboards and execution metrics.

## 📂 Folder Structure
| Folder / File            | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| `DataGenieAPI/`          | Backend FastAPI service for NLP to SQL translation and execution             |
| `DataGenieUI/`           | Angular-based frontend user interface                                        |
| `Logs/`                  | Execution logs and error tracebacks                                          |
| `TestResults/`           | HTML test reports and graph-based visualizations                             |
| `DataGenie-Final.png`    | Final architecture or system diagram for submission                         |
| `test_results.html`      | Auto-generated test case results summary                                     |
| `README.md`              | Setup instructions and documentation                                         |

## ⚙️ Setup Instructions

### 1. 🔧 Prerequisites
- Python 3.8+
- Node.js and Angular CLI (for frontend)
- SQL Server with necessary stored procedures
- Azure OpenAI GPT-4o deployed in your Azure subscription

### 2. 🧱 Backend Installation
```bash
cd DataGenieAPI
pip install -r requirements.txt
```

### 3. 📝 Backend Configuration (`config.inf`)
Update the config file with:
```ini
[AZURE]
ENDPOINT = https://your-openai-resource.openai.azure.com
API_KEY = your-azure-key
DEPLOYMENT = gpt-4o
API_VERSION = 2024-04-01-preview

[SMTP]
SERVER = smtp.office365.com
PORT = 587
USER = your@email.com
PASSWORD = your-password

[EMAIL]
TO_EMAILS = abc@example.com, xyz@example.com
```

### 4. 🧠 Schema Metadata
- Place your domain-specific schema file as `schema_template.json` in the root folder.
- This must describe table names, columns, data types, and descriptions.

### 5. 🚀 Run the Backend Server
```bash
cd DataGenieAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. 🌐 Frontend Setup (Angular)
```bash
cd DataGenieUi
npm install
ng serve --port 4200
```
Visit the app at: `http://localhost:4200`

---

## 📡 API Endpoints
| Method | Endpoint                   | Description                            |
|--------|----------------------------|----------------------------------------|
| POST   | `/generate-sql`            | Convert natural language to SQL        |
| POST   | `/execute-sql`             | Execute raw SQL                        |
| POST   | `/generate-and-execute-sql`| End-to-end query + execution           |
| GET    | `/getdashboarddata`        | Fetch prompt usage metrics             |
| GET    | `/fetch-ticket-details`    | View all failed execution tickets      |
| GET    | `/get-ticket-status`       | Get status of a specific ticket        |
| POST   | `/update-ticket-status`    | Resolve or assign ticket               |

---

## 🧪 Testing & Reporting

```bash
python test_automation.py
```
This runs all prompts from `final_test_cases.json` and generates:
- SQL generation success rates
- Execution summaries
- `test_results.html` and PNG charts

---

## 📈 Dashboard Highlights
- ✅ Total prompts processed: 200
- 💡 Success Rate: 94.00%
- 🧠 Intent Generation Accuracy: 100%
- 🚀 Average Turnaround Time: 48.36 seconds

---

## 🔐 Security & Safety
- Filters inappropriate content & non-business prompts
- Only allows SELECT queries
- Flags large table queries with optimization hints

---

## 🧩 Domains Supported
- Toll Transactions
- Liquidation Reports
- Payment Analytics
- Violations & Notice Tracking

---

## 👥 Team Members
- **Arun Siripuram** – Architect  (`asiripuram@viaplus.com`) - Personal email: (`arunk.siripuram@gmail.com`)
- **Avishek** – AI Engineer (`foodasylum70@gmail.com`)  
- **Susmitha** – AI Engineer (`susmithasony13@gmail.com`)  
- **Rishitha** – AI Engineer (`rishithachindukuru27@gmail.com`)

## 📬 Support
For questions or contributions, contact:
**Arun Siripuram** – `asiripuram@viaplus.com`

---

## ✅ Final Note
Data Genie is a domain-adaptable platform. By changing your `schema_template.json` and aligning prompts with your domain vocabulary, you can deploy this tool across transportation, finance, compliance, or customer support platforms.

Empower your teams to talk to data — intelligently.