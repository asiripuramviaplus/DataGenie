import os
import re
import sys
import json
import pyodbc
import pandas as pd
from tabulate import tabulate
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
import time
import logging
import difflib
from datetime import datetime, date
from decimal import Decimal
from intentagentmobility import extract_intent
from db_connection import get_db_connection  # Import get_db_connection function

from logger_config import logger  # Import centralized logger
import configparser


# from auditlogger import SQLAuditLogger
# from dotenv import load_dotenv  # ✅ Import dotenv


# Example - Global initialization
# llama_recommendation_engine = LlamaRecommendationEngine(model_path="path_to_your_llama_model/llama-2-7b-chat.ggmlv3.q4_0.bin")
# ✅ Load Azure API details from config.inf
config = configparser.ConfigParser()
config.read("config.inf")

MAX_ROWS = 500000  # ✅ Set max allowed rows
MAX_SIZE_MB = 20  # ✅ Set max response size in MB

def get_json_size(data):
    """Calculate the JSON size of query results."""
    return sys.getsizeof(json.dumps(data)) / (1024 * 1024)  # Convert bytes to MB

AZURE_OPENAI_ENDPOINT = config.get("AZURE", "ENDPOINT")
AZURE_OPENAI_API_KEY = config.get("AZURE", "API_KEY")
AZURE_OPENAI_DEPLOYMENT = config.get("AZURE", "DEPLOYMENT")
AZURE_OPENAI_API_VERSION = config.get("AZURE", "API_VERSION")

# ✅ Initialize Azure AI Client
model = ChatCompletionsClient(
    endpoint=f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/?{AZURE_OPENAI_API_VERSION}",
    credential=AzureKeyCredential(AZURE_OPENAI_API_KEY),
)
logging.info(f"AZURE_OPENAI_ENDPOINT: {AZURE_OPENAI_ENDPOINT}")
logging.info(f"AZURE_OPENAI_DEPLOYMENT: {AZURE_OPENAI_DEPLOYMENT}")
logging.info(f"AZURE_OPENAI_API_VERSION: {AZURE_OPENAI_API_VERSION}")

logger.info("✅ Azure OpenAI API Client initialized successfully.")

# Retrieve system instructions from the .env file
schema_json_path = "schema_template.json"

def extract_json_from_text(response_text):
    """Extracts the JSON content from a mixed AI response."""
    try:
        # ✅ Ensure JSON starts at the first `{` and ends at the last `}`
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            return match.group(0)  # ✅ Extract the JSON portion
        else:
            logger.error("Failed to extract JSON from AI response.")
            return None
    except Exception as e:
        logger.error(f"Error extracting JSON: {e}")
        return None
    
def load_schema_from_json(file_path):
    """Load schema information from a JSON file."""
    logger.info("Loading schema information from JSON file.")
    try:
        with open(file_path, "r",encoding="utf-8") as json_file:
            schema_info = json.load(json_file)
        logger.info("Schema information loaded successfully.")
        return schema_info
    except Exception as e:
        logger.error(f"Error loading schema from JSON: {e}")
        return None
def analyze_query_complexity(query):
    """Analyze SQL Query complexity based on joins, subqueries, and length."""
    complexity_score = 0
    complexity_factors = {}

    # Measure Query Length
    query_length = len(query)
    complexity_factors["query_length"] = query_length
    if query_length > 500:
        complexity_score += 2  # Longer queries are often complex

    # Count Number of Joins
    join_count = query.lower().count(" join ")
    complexity_factors["join_count"] = join_count
    if join_count > 3:
        complexity_score += 3  # More than 3 JOINs can be expensive

    # Detect Subqueries
    subquery_count = query.lower().count("( select ")
    complexity_factors["subquery_count"] = subquery_count
    if subquery_count > 1:
        complexity_score += 2  # More than 1 subquery increases complexity

    # Detect SELECT * (Bad Practice)
    if "select *" in query.lower():
        complexity_score += 2
        complexity_factors["select_all"] = True
    else:
        complexity_factors["select_all"] = False

    # Final Complexity Level
    if complexity_score >= 5:
        complexity_level = "High"
    elif complexity_score >= 3:
        complexity_level = "Medium"
    else:
        complexity_level = "Low"

    return {
        "complexity_score": complexity_score,
        "complexity_level": complexity_level,
        "complexity_factors": complexity_factors
    }

def validate_and_correct_sql(query, schema_info):
    """Validate and correct SQL query based on JSON schema metadata."""
    logger.info("Validating and correcting SQL query using schema JSON.")
    # logger.info("Schema Info Items:", schema_info.items())  # Print schema info to debug why it's not entering the loop
    
    corrected_query = query
    found_table = None
    
    for table, columns in schema_info.items():
        # Correct table names
        if table.split('.')[-1].lower() in query.lower():
            found_table = table
            logger.info(f"Correcting table name: {table}")
            corrected_query = corrected_query.replace(table.split('.')[-1], table)
    
    if not found_table:
        logger.warning("No matching table found in query. The query may be incorrect.")
    
    # Correct column names
    if found_table:
        for column in schema_info[found_table]:
            matches = difflib.get_close_matches(column.lower(), query.lower().split(), n=1, cutoff=0.8)
            if matches:
                logger.info(f"Correcting column name: {matches[0]} -> {found_table}.{column}")
                corrected_query = corrected_query.replace(matches[0], f"{found_table}.{column}")
    
    logger.info("SQL query validated and corrected successfully.")
    return corrected_query

def extract_sql_query(response_text):
    """Extracts only the SQL query from the AI response by removing explanations."""
    logger.info("Extracting SQL query from AI response.")
    lines = response_text.split("\n")
    sql_lines = []
    recording = False
    for line in lines:
        stripped_line = line.strip().lower()
        if stripped_line.startswith("select"):
            recording = True
        if recording:
            sql_lines.append(line)
    logger.info("SQL query extraction completed.")
    return "\n".join(sql_lines).strip()


def extract_decimal_seconds(time_str):
    """
    Extract float value from 'x.xx seconds' string and round to 4 decimals.
    """
    match = re.match(r"([\d.]+)", time_str)
    if match:
        return round(float(match.group(1)), 4)
    return 0.0

# ✅ Read FLAG from config.inf (Ensuring API Switching)
FLAG = None
if "API" in config and "FLAG" in config["API"]:
    FLAG = config.getint("API", "FLAG")  # Read FLAG as integer (0 or 1)
else:
    logging.warning("⚠️ FLAG not found in config.inf! Please set it to 0 (Mistral) or 1 (Azure API).")

# ✅ Use the FLAG for API switching
flag = FLAG  # Dynamically use the config value


def generate_sql_query(prompt, schema_info, execute_query_flag=False, offset=0, fetch=10):
    from auditlogger import SQLAuditLogger
    from sqlquerycache import SQLQueryCache   # Import the new cache class
    
    """Generate SQL query using Azure AI, validate it, and execute if required."""
    logger.info("Checking cache before generating SQL query.")
    start_time = time.time()
    query_cache = SQLQueryCache()
    # prompt=prompt+".Pls process this carefully"
    existing_query = query_cache.check_existing_query(prompt)
    logging.info(f"Existing Query --- >>: {existing_query}")
    
    if existing_query:
        logger.info("✅ Cached query found. Validating intent before using it.")
        try:
            
            raw_generated_intent = existing_query.get("generated_intent", "{}")
            generated_intent=raw_generated_intent 
            # Check if the string contains "action"
            if '"action"' not in raw_generated_intent and "'action'" not in raw_generated_intent:
                logger.warning("❌ Cached query ignored because the related intent does not contain 'action'.")
                existing_query = None  # Invalidate the cached query
            else:
                logger.info("✅ Cached query is valid and will be used.")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing generated_intent: {e} | Raw Value: {raw_generated_intent}")
            existing_query = None  # Invalidate the cached query
    
    if existing_query:
        logger.info("✅ Cached query found. Using stored SQL query instead of generating a new one.")
        try:
            auditid = existing_query.get("auditid", "{}")
            raw_generated_sql = existing_query.get("generated_sql", "{}")
            logger.info(f"raw_generated_sql Query --- >>: {raw_generated_sql}")
            generated_sql = raw_generated_sql.replace("''", "'") 
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing generated_sql: {e} | Raw Value: {raw_generated_sql}")
            generated_sql = {}

        generated_summary = existing_query["generated_summary"]
        recommendations = existing_query["generated_recommendations"]
         # ✅ Fix query_complexity parsing
        try:
            raw_query_complexity = existing_query.get("query_complexity", "{}")
            logger.info(f"raw_query_complexity Query --- >>: {raw_query_complexity}")
            query_complexity = raw_query_complexity.replace("''", "'") 
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing query_complexity: {e} | Raw Value: {raw_query_complexity}")
            query_complexity = {}

        logger.info(f"Generated SQL -----> {generated_sql}")
        query_cache.close_connection()  # Close connection
    else:
        auditid = 0
        logger.info("❌ No matching query located in cache. Proceeding with new SQL generation")
        logger.info("Generating SQL query from plain English prompt.")
        
    
        with open(schema_json_path, "r", encoding="utf-8") as file:
            schema_info = json.load(file)

        schema_text = "\n".join([
            (
                f"Table: {table}\n"
                f"Columns: {', '.join(['{} ({})'.format(column.get('Column'), column.get('DataType')) for column in details.get('Columns', [])]) if details.get('Columns') else 'Not Provided'}\n"
                f"RowCount: {details.get('RowCount', 'Unknown')}\n"
                f"MasterDataValues: {details.get('MasterDataValues', 'Unknown')}\n"
                f"Description: {details.get('Description', 'This table contains relevant data.')}"
            )
            for table, details in schema_info.items()
        ])

        logger.info("Generating the intent of the user processing the prompt further")
        intent = extract_intent(prompt,flag)  # Pass flag only for intent extraction
        logger.info(f"\n✅ Extracted Intent:\n {intent}")

        # Parse string to dict if needed
        if isinstance(intent, str):
            try:
                intent = json.loads(intent)
            except Exception as e:
                logger.error(f"❌ Failed to parse extracted intent JSON: {e}")
                return {
                    "generated_summary": "ERROR",
                    "generated_sql": None,
                    "generated_recommendations": [],
                    "query_complexity": {},
                    "validation_warnings": [],
                    "missing_tables": [],
                    "generation_time": "0.00 seconds",
                    "message": "Unable to parse intent. Please retry."
                }

        # ✅ If optimized_schema is empty, stop SQL generation and return intent message
        if intent.get("optimized_schema", "{}").strip() == "{}":
            logger.warning("❌ SQL generation skipped — 'optimized_schema' is empty or not aligned with the Mobility Platform schema.")
            return {
                "generated_summary": intent.get("summary", "Insufficient details to generate SQL."),
                "generated_sql": intent.get("query", "no query generated"),
                "generated_recommendations": [intent.get("recommendations", "Please provide more specific details.")],
                "query_complexity": {},
                "validation_warnings": [],
                "missing_tables": [],
                "generation_time": "0.00 seconds",
                "message": "SQL query not generated due to missing schema information.",
                "execution_allowed": False,  # ⬅️ Important for frontend logic
            }

        try:
            response = model.complete(
            model=AZURE_OPENAI_DEPLOYMENT,  # Replaced gpt-4o with AZURE_OPENAI_DEPLOYMENT
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an advanced AI assistant that specializes in generating optimized SQL Server queries with a fair understanding in Mobility Platform. The users are encouraged to provide natural language statement as they are non-technical"
                        "You will be provided with an INTENT that includes a detailed JSON schema, containing descriptions of corresponding tables and their columns, along with data types. Strictly adhere to the provided table names and column names as they are, without deviation. Do not assume or fabricate any additional columns, tables, or relationships. The provided schema should be followed exactly as stated to ensure accurate data handling and query generation. the intent is :"
                        f"{intent}\n\n"
                        "Use the chat history from the intent only for the specific query it belongs to. Do not use the context from one query for other unrelated queries"
                        #"When the user request includes both a total count and detailed data retrieval, generate a single SQL query using COUNT(*) OVER() to avoid multiple queries. This ensures efficient execution by calculating the count once and returning it for all rows."
                        "Ensure correct SQL syntax by placing operations in the appropriate clauses, avoiding ambiguous references, and maintaining proper logic flow across filtering, grouping, and ordering. Always explicitly define columns in SELECT and validate query structure to prevent errors."
                        "Carefully analyze the optimized schema to accurately identify table and column names, their relationships, and always list columns explicitly—never use * "
                        #"Always include an explicit column-based ORDER BY clause when pagination (OFFSET, FETCH) is used.\n"
                        "If the request is vague (e.g., `Give me all transactions`), ask the user to **narrow down** the criteria"
                        "Exclude PrimaryKey columns which are ID's, CREATEDDATE, UPDATEDDATE, UPDATEDUSER, CREATEDUSER , CREATEDBY,  UPDATEDBY columns from the SELECT statement. "
                        "Use the actual column name strictly from intent in the SELECT clause, and assign a readable alias with spaces using `AS [...]'. For example: `InvoiceMonthYear AS [Invoice Month Year]. Do not replace the original column name with only an alias"
                        #"Always format any date fields in US date format (MM/dd/yyyy) when constructing the SQL query"
                        "Always use single quotes ' for format strings in SQL Server functions like FORMAT(). Do not escape them with double single-quotes '', as this causes syntax errors. Ensure that the date format string is written as 'MM/dd/yyyy' or 'MM/dd/yyyy HH:mm:ss' within the FORMAT() function. Do not wrap the entire function in additional quotes."
                        "Do not use tuple comparisons like (col1, col2) IN (SELECT col1, col2 FROM ...) as this syntax is not supported in SQL Server. Instead, use an INNER JOIN or EXISTS with separate column conditions to achieve the same logic. For example, to filter based on the latest record per group, use a subquery to get the MAX date grouped by a key, then join it back on both the key and the date."
                        "Avoid using functions like DATE_TRUNC, which are not supported in SQL Server. Instead, use DATEPART() and DATEADD() for date-based filtering, such as quarters, months, or years. For example, use DATEPART(QUARTER, ColumnName) and compare with DATEPART(QUARTER, DATEADD(MONTH, -3, GETDATE()))."
                        "Avoid using MySQL-specific functions like DATE_SUB(..., INTERVAL ...) in SQL Server. Use DATEADD(unit, value, date) instead. For example, replace DATE_SUB(GETDATE(), INTERVAL 30 DAY) with DATEADD(DAY, -30, GETDATE())"
                        "Include column name headers in the query results. Always provide your answer in the JSON format below: { \"summary\": \"your-summary\", \"query\": \"your-query\" ,\"recommendations\": \"your-recommendations\"  }"
                        "HV stands for Habitual Violator,C stands for Credit, D for Debit. please read the descriptions carefully provided in the schema"
                        "If the dataset is large, suggest optimizations such as filtering with more clauses, and using aggregations. Please dont recommend any SQL Server related optimisations as these messages are shown to the end users" 
                        # "**Avoid any SQL Server-specific optimizations, as these messages are meant for end users who are not technical.** "
                        "When suggesting optimizations, phrase them in simple terms without referencing SQL functions or indexing strategies. "
                        "Recommend using **general filtering suggestions** rather than specific column names. DONT include pagination clauses like OFFSET or FETCH NEXT in the SQL query"
                        #"use `TOP` for limiting results instead of `LIMIT` to align with SQL Server specific syntax. "
                        "Use TOP for limiting results instead of LIMIT, and place TOP immediately after the SELECT keyword, like:"
                        "SELECT TOP 5 column1, column2 FROM ..."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )

            response_text = response.choices[0].message.content.strip()
            if not response_text:
                logger.error("AI response is empty. Cannot generate SQL.")
                return {
                    "generated_summary": "ERROR",
                    "generated_sql": None,
                    "generated_recommendations": [],
                    "query_complexity": {},
                    "validation_warnings": [],
                    "missing_tables": [],
                    "generation_time": "0.00 seconds",
                    "message": "SQL generation failed."
                }

            json_response = extract_json_from_text(response_text)
            response_json = json.loads(json_response)
            generated_summary = response_json.get("summary", "No summary available.")
            generated_sql = response_json.get("query", "No Query generated").strip()
            recommendations = response_json.get("recommendations", [])
            query_complexity = analyze_query_complexity(generated_sql)
            generated_intent = intent

            if not generated_sql:
                return {
                    "generated_summary": generated_summary,
                    "generated_sql": "No Query generated, please check recommendations",
                    "generated_recommendations": recommendations,
                    "query_complexity": query_complexity,
                    "validation_warnings": [],
                    "missing_tables": [],
                    "generation_time": f"{time.time():.2f} seconds",
                    "message": "SQL generation failed."
                }
            
            # ✅ Validate if the query is SELECT-only
            if not generated_sql.lower().startswith("select"):
                logger.error(f"Blocked Non-SELECT Query: {generated_sql}")
                return {
                    "generated_summary": "This tool is designed to retrieve data and help you analyze information. It does not support deleting, modifying, or altering database records. Please try again with a request to fetch the data you need",
                    "generated_sql": "Query blocked due to safety restrictions (only SELECT queries are allowed).",
                    "message": "Only SELECT queries are allowed. The query was blocked.",
                    "execution_allowed": False,  # ⬅️ Important for frontend logic
                    "generated_recommendations": [],
                }

            
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            return {
                "generated_summary": "ERROR",
                "generated_sql": None,
                "generated_recommendations": [],
                "query_complexity": {},
                "validation_warnings": [],
                "missing_tables": [],
                "generation_time": "0.00 seconds",
                "message": "An error occurred while generating SQL."
            }
    execution_time = time.time() - start_time
    if execute_query_flag:
        conn = get_db_connection()
        if not conn:
            return {
                "generated_summary": generated_summary,
                "generated_sql": generated_sql,
                "generated_recommendations": recommendations,
                "query_complexity": query_complexity,
                "validation_warnings": [],
                "missing_tables": [],
                "generation_time": f"{execution_time - start_time:.2f} seconds",
                "execution_result": {
                    "columns": [],
                    "rows": [],
                    "message": "Database connection failed.",
                    "message_code": 500,
                    "execution_time": "0.00 seconds",
                    "query_status": "Query Not Executed",
                    "row_count": None,
                    "data_size_mb": None,
                    "total_records": None
                }
            }
        # result = execute_query(conn, generated_sql, offset, fetch)
            # Execute query and retrieve results
        logger.error(f"Generated SQL before sending for execution ---->>>>>>>: {generated_sql}")
        result=execute_query(conn=conn,query=generated_sql, offset=offset, fetch=fetch, attempts=0, intent=generated_intent)
        is_reused_prompt = 1 if existing_query else 0
        total_records = result.get("total_records", 0)
        executed_sql = result.get("executed_sql", generated_sql)  # Get executed SQL
        generation_time = f"{time.time():.2f}"
        exec_time = execution_time
        audit_logger = SQLAuditLogger()
        # logger.info(f"execution_result --->: {str(result.get('query_status', [])) if execute_query_flag else ''}")
        # logger.info(f"auditid --->: {auditid}")
        audit_data = {
            'AuditId': auditid,
            'Prompt': prompt,
            'GeneratedSQL': generated_sql,
            'Summary': generated_summary,
            'Recommendations': recommendations if recommendations else '',
            'GenerationTime': round(execution_time, 4) if execute_query_flag else 0,
            'ExecutionTime': str(result.get("execution_time", 0)).replace(" seconds", "").replace(" ", ""),
            'QueryComplexity': str(query_complexity),
            'Message': result.get("execution_result", {}).get("message", "Generated") if execute_query_flag else "Generated",
            'TotalRecords': total_records if execute_query_flag else 0,
            'ExecutionResults': str(result.get('query_status', [])) if execute_query_flag else '',
            'IsSQLGenerationSuccess': 1 if generated_sql else 0,
            'IsExecutionSuccess': 1 if result.get("message_code", 0) in [200, 204] else 0,
            'ErrorMessage': last_sql_error if last_sql_error else "",
            'IsIntentGenerated': 1 if generated_intent and str(generated_intent).strip() not in ['{}', '[]', ''] else 0,
            'IntentGeneratedData': generated_intent,
            'IsReusedPrompt': 1 if is_reused_prompt else 0,
            'OverallStatus': "Success" if (
                result.get("message_code", 0) in [200, 204]  and 
                generated_intent and str(generated_intent).strip() not in ['{}', '[]', '']
            ) else "Failed",
            'CreatedUser': 'System',  # or dynamic username
            'UpdatedUser': 'System'
        }

        #audit_logger.log_audit_record(audit_data)
        ticket_number = audit_logger.log_audit_record(audit_data)
        
        audit_logger.close()
        # logger.info(f"Executed SQL Query-------->: {executed_sql}")
        conn.close()
        return {
            "generated_summary": generated_summary,
            "generated_sql": executed_sql,
            "generated_recommendations": recommendations if (total_records and total_records > 0) else [],
            "query_complexity": query_complexity,
            "validation_warnings": [],
            "missing_tables": [],
            "generation_time": f"{execution_time:.2f} seconds",
            "execution_result": result,
            "ticket_number": ticket_number
        }

    return {
        "generated_summary": generated_summary,
        "generated_sql": generated_sql,
        "generated_recommendations": recommendations if (total_records and total_records > 0) else [],
        "query_complexity": query_complexity,
        "validation_warnings": [],
        "missing_tables": [],
        "generation_time": f"{execution_time:.2f} seconds",
        "ticket_number": ticket_number,
        "intent" :intent

    }
    


def serialize_row(row, columns):
    """Convert datetime and decimal objects to JSON-serializable strings and remove newlines."""
    serialized_row = {}
    for col, value in zip(columns, row):
        if isinstance(value, (datetime, date)):
            serialized_row[col] = value.isoformat()
        elif isinstance(value, Decimal):
            serialized_row[col] = float(value)
        else:
            serialized_row[col] = str(value).replace("\n", " ")
    return serialized_row

def execute_query(conn=None, query=""):
    from db_connection import get_new_db_connection
   # if audit logger is used
    
    """Execute the SQL query using a shared connection if provided."""
    logger.info("Executing SQL query.")

    close_conn = False
    if conn is None:
        conn = get_new_db_connection()  # ✅ Use the shared DB connection
        if not conn:
            return {
                "columns": [],
                "rows": [],
                "message": "Database connection failed",
                "message_code": 500,
                "query_status": "Query Failed",
                "row_count": None,
                "data_size_mb": None
            }
        close_conn = True  # Close only if we created it

    try:
        query = query.replace("\n", " ")  # ✅ Remove newline characters
        cursor = conn.cursor()
        cursor.execute(query)

        # ✅ Extract column names
        columns = [column[0] for column in cursor.description]

        # ✅ Fetch all results and serialize datetime/decimal values
        rows = [serialize_row(row, columns) for row in cursor.fetchall()]
        row_count = len(rows)

        # ✅ Check Row Count Limit
        if row_count > MAX_ROWS:
            logger.warning(f"Query returned {row_count} rows. Exceeds max limit of {MAX_ROWS}.")
            return {
                "columns": columns,
                "rows": [],
                "message": "Query result exceeds row limit.",
                "message_code": 413,
                "query_status": "Query Partially Executed",
                "row_count": row_count,
                "data_size_mb": None
            }

        # ✅ Check Data Size Limit
        data_size = get_json_size(rows)
        if data_size > MAX_SIZE_MB:
            logger.warning(f"Query result size {data_size:.2f}MB exceeds limit of {MAX_SIZE_MB}MB.")
            return {
                "columns": columns,
                "rows": [],
                "message": "Query result exceeds size limit.",
                "message_code": 413,
                "query_status": "Query Partially Executed",
                "row_count": row_count,
                "data_size_mb": data_size
            }

        logger.info(f"SQL query executed successfully. {row_count} rows, {data_size:.2f}MB size.")

        return {
            "columns": columns,
            "rows": rows,  # ✅ JSON-safe data
            "message": "Records found" if row_count > 0 else "No records found",
            "message_code": 200 if row_count > 0 else 204,
            "query_status": "Query Executed Successfully",
            "row_count": row_count,
            "data_size_mb": data_size
        }

    except pyodbc.ProgrammingError as e:
        logger.error(f"SQL Programming Error: {e}")
        return {
            "columns": [],
            "rows": [],
            "message": "SQL Syntax Error",
            "message_code": 400,
            "query_status": "Query Failed",
            "row_count": None,
            "data_size_mb": None
        }

    except pyodbc.InterfaceError as e:
        logger.error(f"Database Connection Issue: {e}")
        return {
            "columns": [],
            "rows": [],
            "message": "Database Connection Error",
            "message_code": 503,
            "query_status": "Query Failed",
            "row_count": None,
            "data_size_mb": None
        }

    except pyodbc.Error as e:
        logger.error(f"ODBC Error: {e.args[0]}, {e.args[1]}")
        return {
            "columns": [],
            "rows": [],
            "message": f"SQL Execution Error: {e.args[1]}",
            "message_code": 500,
            "query_status": "Query Failed",
            "row_count": None,
            "data_size_mb": None
        }

    except Exception as e:
        logger.error(f"General Error executing SQL query: {e}")
        return {
            "columns": [],
            "rows": [],
            "message": "SQL Execution Error",
            "message_code": 500,
            "query_status": "Query Failed",
            "row_count": None,
            "data_size_mb": None
        }

    finally:
        if close_conn:
            conn.close()  # ✅ Close connection only if created inside

last_sql_error = None  
# def execute_query(conn=None, query="", offset=0, fetch=10, total_records=None):
def execute_query(conn=None, query="", offset=0, fetch=10, total_records=None, attempts=0, intent=None):
    from db_connection import get_new_db_connection

    global last_sql_error  # Use the global variable
    close_conn = False
    logger.info(f"\nattempts --->>>: {attempts}")
    conn = get_new_db_connection()
    if not conn:
        return {
                "columns": [], "rows": [],
                "message": "Database connection failed",
                "message_code": 500, "query_status": "Query Failed",
                "row_count": None, "data_size_mb": None, "total_records": None,
                "execution_time": "0.00 seconds"
            }
    close_conn = True

    try:
        start_time = time.time()
        cursor = conn.cursor()
        original_query = query.rstrip(';').strip()
        logger.error(f"inside execution---->>>>>>>: {original_query}")

        count_query = None

        # ✅ Robust pagination cleanup
        query_without_pagination = re.sub(
            r'ORDER\s+BY\s+[\w\[\]\.\s,]+?\s+OFFSET\s+\d+\s+ROWS\s+FETCH\s+NEXT\s+\d+\s+ROWS\s+ONLY',
            '',
            original_query,
            flags=re.IGNORECASE | re.DOTALL
        )

        # ✅ Continue with alias fix
        paginated_query = re.sub(
            r'AS\s+([\w ]+)',
            lambda m: f'AS [{m.group(1).strip()}]' if ' ' in m.group(1) else m.group(0),
            query_without_pagination,
            flags=re.IGNORECASE
        )

        # ✅ Step 3: Calculate total records if not provided
        if total_records is None:
            if not re.match(r'^SELECT\s+COUNT\(\*\)', paginated_query, flags=re.IGNORECASE):
                count_query_clean = re.sub(r'ORDER\s+BY[\s\S]*$', '', paginated_query, flags=re.IGNORECASE)
                count_query = f"SELECT COUNT(*) FROM ({count_query_clean}) AS total_count_query"
            else:
                count_query = paginated_query

            logger.info(f"Executing Count Query: {count_query}")
            
            cursor.execute(count_query)
            total_records = cursor.fetchone()[0]
            logger.info(f"Total Records Found inside execute--->>>: {total_records}")

        # ✅ Remove existing pagination clauses if accidentally present
        paginated_query = re.sub(
            r'OFFSET\s+\d+\s+ROWS\s+FETCH\s+NEXT\s+\d+\s+ROWS\s+ONLY',
            '',
            paginated_query,
            flags=re.IGNORECASE
        ).strip()

        logger.error(f"inside execution paginated_query---->>>>>>>: {paginated_query}")

        # is_aggregate_query = (
        #     re.search(r'SELECT\s+(.*?)\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', paginated_query, re.IGNORECASE) or
        #     re.search(r'\bGROUP\s+BY\b', paginated_query, re.IGNORECASE)
        # )
        
        # Check if the query contains an aggregation function
        has_aggregation = bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX)\s*\(', paginated_query, re.IGNORECASE))

        # Check if the query contains GROUP BY (meaning multiple rows could be returned)
        has_group_by = bool(re.search(r'\bGROUP\s+BY\b', paginated_query, re.IGNORECASE))

        # Allow pagination if GROUP BY is present
        is_aggregate_query = has_aggregation and not has_group_by


        # ✅ Step 4: Ensure ORDER BY exists only if NOT an aggregate query
        if not is_aggregate_query and not re.search(r'ORDER\s+BY', paginated_query, flags=re.IGNORECASE):
            cursor.execute(paginated_query)
            first_column = cursor.description[0][0]
            paginated_query += f" ORDER BY [{first_column}]"
            logger.info(f"'ORDER BY' added using first column: {first_column}")
        else:
            logger.info("Skipping ORDER BY addition due to aggregate query or existing ORDER BY.")

        is_count_only_query = bool(re.match(r'^\s*SELECT\s+COUNT\(\*\)', paginated_query, re.IGNORECASE))

        # ✅ Apply pagination only if it's NOT a COUNT(*) and NOT an aggregate and needed
        if not is_count_only_query and not is_aggregate_query and total_records > fetch:
            paginated_query += f" OFFSET {offset} ROWS FETCH NEXT {fetch} ROWS ONLY"
            logger.info(f"Pagination applied with OFFSET {offset} and FETCH {fetch}")
        else:
            logger.info("Skipping pagination (COUNT(*) query, aggregate query, or small result set).")

        # ✅ Final execution
        logger.info(f"Final Executed Paginated Query --->>>: {paginated_query}")
        cursor.execute(paginated_query)

        columns = [column[0] for column in cursor.description]
        rows = [serialize_row(row, columns) for row in cursor.fetchall()]
        execution_time = time.time() - start_time
        logger.info(f"Execution Time----->: {execution_time:.2f} seconds")

        if len(rows) < total_records and count_query==paginated_query:
            logger.warning(f"Mismatch: Total records ({total_records}) vs Retrieved rows ({len(rows)})")
            total_records = len(rows)  # Adjust to correct value
            

        return {
            "columns": columns,
            "rows": rows,
            "executed_sql": paginated_query,
            "message": "Records found" if rows else "No records found",
            "message_code": 200 if rows else 204,
            "query_status": "Query Executed Successfully",
            "row_count": len(rows),
            "data_size_mb": get_json_size(rows),
            "total_records": total_records,
            "execution_time": f"{execution_time:.2f} seconds"
        }

    except pyodbc.Error as e:
        last_sql_error = ' | '.join(str(arg) for arg in e.args)
  
        logger.error(f"SQL Execution Error: {e}")
        
        if attempts < 3:
            logger.warning(f"Retrying SQL Correction (Attempt {attempts + 1})")
            corrected_sql = get_corrected_sql(
                generated_sql=query,
                error_message = last_sql_error,
                intent=intent
            )
            if corrected_sql:
                return execute_query(
                    conn=conn,
                    query=corrected_sql,
                    offset=offset,
                    fetch=fetch,
                    total_records=total_records,
                    attempts=attempts + 1,
                    intent=intent
                )
        return {
            "columns": [], "rows": [],
            "message": f"SQL Execution Error: {e.args[1]}",
            "message_code": 500, "query_status": "Query Failed",
            "row_count": None, "data_size_mb": None, "total_records": None,
            "execution_time": "0.00 seconds"
        }

    finally:
        if close_conn:
            conn.close()

def get_corrected_sql(generated_sql, error_message, intent):
    try:
        
        messages = [
        {
            "role": "system",
            "content": (
                "You are an expert SQL assistant specialized in debugging and correcting SQL Server queries. "
                "You will be given a broken or invalid SQL Server query, the associated SQL Server error message, and an optimized schema. "
                "The schema contains all valid table names, their columns, and descriptions of what each table represents.\n\n"
                "Your responsibilities:\n"
                "- Correct all types of issues in the SQL Server query: syntax errors, logical bugs, ambiguous references, type mismatches, and dialect mismatches.\n"
                "- Fix SQL dialect issues (e.g., MySQL-style backticks) by converting them to valid SQL Server syntax.\n"
                "- Eliminate hallucinated or incorrect table/column names, aliases, or functions.\n"
                "- Use only the **provided schema** to determine the correct table and column names. **Never guess or invent new names**.\n"
                "- Use table and column descriptions from the schema to infer user intent and make logical corrections.\n"
                "- If a column or table is not in the schema, remove it or replace it with the correct one from the schema.\n\n"
                "**Important Instructions:**\n"
                "- Assume the SQL dialect is always SQL Server.\n"
                "- Only output the corrected SQL query.\n"
                "- Do NOT add explanations, markdown, or comments.\n"
                "- Ensure all identifiers match the schema exactly (case-insensitive)."
            )
        },
        {
            "role": "user",
            "content": (
                "The following SQL query failed:\n\n"
                f"{generated_sql}\n\n"
                f"Error message:\n{error_message}\n\n"
                f"Optimized Schema:\n{intent}\n\n"
                "Please correct the query and return only the fixed SQL query without any prefix or suffix"
            )
        }
]

        response = model.complete(
            model="gpt-4o",
            messages=messages,
        )

        fixed_sql = response.choices[0].message.content.strip()
        logger.info(f"Corrected SQL received from Azure OpenAI:\n{fixed_sql}")
        fixed_sql = fixed_sql.replace("`", "")
        return fixed_sql

    except Exception as ex:
        logger.error(f"Failed to get corrected SQL: {ex}")
        return None

def display_results(columns, rows):
    logger.info("Displaying query results.")
    if columns and rows:
        logger.info("\nQuery Results:")
        logger.info(tabulate(rows, headers=[f"**{col}**" for col in columns], tablefmt="grid", stralign="center"))
    else:
        logger.info("No results or error executing the query.")

def main():
    logger.info("Starting the application.")
    # conn = connect_to_database(db_config)
    # schema_info = load_schema_from_json(schema_json_path)
    # if not conn:
    #     logger.error("Database connection failed. Exiting application.")
    #     return

    # while True:
    #     user_input = input("\nEnter your query in plain English (or type 'exit' to quit): ")
    #     if user_input.lower() == "exit":
    #         logger.info("User exited the application.")
    #         break

    #     sql_query = generate_sql_query(user_input, schema_info)
    #     if not sql_query:
    #         logger.warning("Failed to generate SQL query. Prompt user to try again.")
    #         logger.info("Could not generate SQL query. Please try again.")
    #         continue

    #     execute = input("\nDo you want to execute this query? (yes/no): ").strip().lower()
    #     if execute == "yes":
    #         columns, rows = execute_query(conn, sql_query)
    #         display_results(columns, rows)

    # conn.close()
    logger.info("Application terminated.")
    logger.info("Goodbye!")

if __name__ == "__main__":
    main()
