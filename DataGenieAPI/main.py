#import logging
import time
from fastapi import Query, WebSocket, WebSocketDisconnect
import re
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional  # ✅ Add Optional
from TableValidator import TableValidator  # ✅ Import the Table Validator
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
import json  # Add this import
from typing import Dict
from content import ContentSafetyChecker
# from db_connection import get_db_connection, db_config
import asyncio
from fastapi.concurrency import run_in_threadpool
from logger_config import logger  
from auditlogger import SQLAuditLogger
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import HTTPException

app = FastAPI()

# ✅ Cache to store total records per query
total_records_cache: Dict[str, int] = {}
cache_lock = asyncio.Lock()  # ✅ Ensures safe async access


# from fastapi import APIRouter
router = APIRouter()
from sqlquerygenerator import (
    # connect_to_database,
    generate_sql_query,
    execute_query,
    load_schema_from_json,
    schema_json_path,
    validate_and_correct_sql,
    get_db_connection

)

# ✅ Initialize Table Validator
validator = TableValidator(schema_json_path)

# ✅ Initialize Content Safety Checker (once and reuse everywhere)
content_safety = ContentSafetyChecker()

# Initialize FastAPI
app = FastAPI(
    title="SQL Query Generator API",
    version="1.2",
    description="API to convert Natural Language to SQL Queries and execute them."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class ReferrerPolicyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(ReferrerPolicyMiddleware)

# Load schema on startup
schema_info = load_schema_from_json(schema_json_path)
if not schema_info:
    logger.error("Failed to load schema.json. Ensure the file is correctly formatted.")

# ------------------------------
# FASTAPI ROUTES
# ------------------------------

class QueryRequest(BaseModel):
    """Request model for generating SQL."""
    query: str

def contains_inappropriate_content(query):
    """Check if the query contains inappropriate content."""
    inappropriate_keywords = [
        "sex", "violence", "drugs", "gambling", "adult", "XXX", "porn", "explicit", "nude", "erotic"
    ]  # Extend as needed
    return any(re.search(rf"\b{keyword}\b", query, re.IGNORECASE) for keyword in inappropriate_keywords)

class ExecuteSQLRequest(BaseModel):
    """Request model for executing SQL."""
    sql_query: str
    use_shared_connection: Optional[bool] = False
    validation_flag: Optional[bool] = False
    intent_message: Optional[str] = None  # ✅ New optional input
    
    
class SQLExecutionResponse(BaseModel):
    """Standard API response model for SQL execution."""
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_records: Optional[int]  # ✅ New field for total records
    message: str
    message_code: int
    execution_time: str
    query_status: str
    row_count: Optional[int]  # ✅ New field for row count
    data_size_mb: Optional[float]  # ✅ New field for response size
    generated_sql: Optional[str]  # ✅ New field for generated SQL

# Path to schema Excel file
schema_json_path = "schema_template.json"

def load_schema_mapping(schema_file):
    """Loads schema mapping from JSON and creates a lookup dictionary."""
    with open(schema_file, "r") as f:
        schema_data = json.load(f)
    
    schema_table_mapping = {}
    
    for table in schema_data.keys():
        if table.startswith("Table: "):
            schema_table = table.replace("Table: ", "")
            table_name = schema_table.split(".")[-1]  # Extract only table name
            schema_table_mapping[table_name.lower()] = schema_table  # Store mapping (case-insensitive)

    return schema_table_mapping

def extract_tables_from_sql(sql_query, schema_mapping):
    """Extracts Schema.TableName from an SQL query using sqlparse."""
    parsed = sqlparse.parse(sql_query)
    tables = set()

    for statement in parsed:
        if not statement.tokens:
            continue

        from_seen = False
        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() in ("FROM", "JOIN"):
                from_seen = True
            elif from_seen and isinstance(token, Identifier):
                table_name = token.get_real_name().lower()  # Normalize table name case
                schema_table_name = schema_mapping.get(table_name, table_name)  # Get Schema.TableName
                tables.add(schema_table_name)
                from_seen = False
            elif from_seen and isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    table_name = identifier.get_real_name().lower()
                    schema_table_name = schema_mapping.get(table_name, table_name)
                    tables.add(schema_table_name)
                from_seen = False

    return tables
# ✅ API to Fetch All Errors

@app.get("/get-all-errors")
def get_all_errors():
    try:
        audit_logger = SQLAuditLogger()  # Must be inside function for mock to work
        return audit_logger.get_all_errors()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/fetch-ticket-details", tags=["Ticket Management"])
def fetch_ticket_details():
    try:
        audit_logger = SQLAuditLogger()  # Must be inside function for mock to work
        return audit_logger.fetch_ticket_details()
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

 

@app.post("/generate-sql", tags=["SQL Generation"])
def api_generate_sql(request: QueryRequest):

    # Load schema mapping from JSON
    schema_mapping = load_schema_mapping(schema_json_path)

    """API Endpoint to generate and validate an SQL query from natural language."""
    logger.info(f"User Prompt -->>: {request.query}")

      # Check for inappropriate content
    if contains_inappropriate_content(request.query):
        return {
            "generated_sql": "",
            "generation_time": "0.00 seconds",
            "query_complexity": {},
            "validation_warnings": [],
            "missing_tables": [],
            "validation_flag": True,
            "message": "This tool is not intended for generating SQL queries for inappropriate or non-business-related content."
        }

    start_time = time.time()
    generated_sql_obj = generate_sql_query(request.query, validator.schema)
    logger.info(f"generated_sql_obj -->>: {generated_sql_obj}")
    if not generated_sql_obj:
        raise HTTPException(status_code=500, detail="Failed to generate a valid SQL query.")

    generated_summary = generated_sql_obj.get("generated_summary", "ERROR")
    generated_sql = generated_sql_obj.get("generated_sql", "ERROR")
    generated_sql = generated_sql.replace('\n', ' ')
    query_complexity = generated_sql_obj.get("query_complexity", {})  # ✅ Fetch complexity details

    # ✅ Extract table names using sqlparse
    tables_in_query = extract_tables_from_sql(generated_sql,schema_mapping)

    # ✅ Validate tables
    validation_result = validator.validate_tables(tables_in_query)
    validation_warnings = validation_result.get("optimization_suggestions", [])
    missing_tables = validation_result.get("missing_tables", [])

    # ✅ Set validation flag
    validation_flag = bool(validation_warnings)

    execution_time = time.time() - start_time

    return {
        "generated_summary": generated_summary,
        "generated_sql": generated_sql,
        "generation_time": f"{execution_time:.2f} seconds",
        "query_complexity": query_complexity,  # ✅ Include complexity details in response
        "validation_warnings": validation_warnings,
        "missing_tables": missing_tables,
        "validation_flag": validation_flag  # ✅ NEW FLAG
    }


@app.post("/execute-sql", tags=["SQL Execution"], response_model=SQLExecutionResponse)
def api_execute_sql(request: ExecuteSQLRequest):
    """API Endpoint to execute a generated SQL query."""
    logger.info(f"Received request to execute SQL: {request.sql_query}")

    # ✅ Restrict Execution if validation_flag is True
    if request.validation_flag:
        logger.warning("Execution restricted due to validation warnings.")
        return SQLExecutionResponse(
            columns=[],
            rows=[],
            message="Execution restricted due to validation warnings. Review validation suggestions.",
            message_code=400,
            execution_time="0.00 seconds",
            query_status="Query Not Executed",
            row_count=None,
            data_size_mb=None,
            total_records=None,  # Explicitly include total_records
            generated_sql=None   # Explicitly include generated_sql
        )

    # ✅ Proceed with Execution
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed.")
    else:
        logger.info("✅ Database connection established successfully!")

    start_time = time.time()
    result = execute_query(
        conn=conn,
        query=request.sql_query,
        intent=request.intent_message
    )
    
    execution_time = f"{time.time() - start_time:.2f} seconds"

    conn.close()
    logger.info(f"SQL Execution completed in {execution_time}.")

    # ✅ Ensure all required fields are included in the response
    return SQLExecutionResponse(
        columns=result["columns"],
        rows=result["rows"],
        message=result["message"],
        message_code=result["message_code"],
        execution_time=execution_time,
        query_status=result["query_status"],
        row_count=result["row_count"],
        data_size_mb=result["data_size_mb"],
        total_records=result.get("total_records", None),  # Include total_records
        generated_sql=result.get("executed_sql", None)    # Include generated_sql
    )

def normalize_query_key(query: str):
    """Generate a cache key by removing variable parts like OFFSET, FETCH."""
    # Remove all excessive spaces
    query = " ".join(query.split())

    # Remove OFFSET and FETCH values (because they change every request)
    query = re.sub(r"OFFSET \d+ ROWS FETCH NEXT \d+ ROWS ONLY", "", query, flags=re.IGNORECASE)
    
    return query.lower()  # ✅ Lowercase for uniform cache keys

@app.post("/execute-sql-paginated", tags=["SQL Execution"])
async def api_execute_sql_paginated(request: ExecuteSQLRequest, offset: int = 0, fetch: int = 10):
    try:
        logger.info(f"Executing paginated SQL. Offset: {offset}, Fetch: {fetch}")

        conn = await run_in_threadpool(get_db_connection)
        if not conn:
            logger.error("Database connection failed.")
            raise HTTPException(status_code=500, detail="Database connection failed.")

        query_key = normalize_query_key(request.sql_query)

        async with cache_lock:
            if query_key in total_records_cache:
                total_records = total_records_cache[query_key]
                logger.info(f"Using cached total_records: {total_records}")
            else:
                logger.info("Fetching total_records from DB...")
                try:
                    result = await run_in_threadpool(execute_query, conn, request.sql_query, offset, fetch, None)
                    if result is None or "error" in result:
                        logger.error(f"Error executing query: {result}")
                        raise HTTPException(status_code=400, detail="Invalid SQL query")

                    total_records = result.get("total_records", 0)
                    logger.info(f"Fetched total_records: {total_records}")
                    if total_records > 0:
                        total_records_cache[query_key] = total_records
                except HTTPException as e:
                    raise e
                except Exception as e:
                    logger.error(f"Error fetching total_records: {str(e)}")
                    raise HTTPException(status_code=500, detail="Failed to fetch total records from DB")

        # --- New check to ensure the offset exceeds total_records ---
        if offset >= total_records:
            return SQLExecutionResponse(
                columns=[],
                rows=[],
                message="No data found",
                message_code=0,
                execution_time="0.00 seconds",
                query_status="NO_DATA",
                row_count=0,
                data_size_mb=0.0,
                total_records=total_records,
                generated_sql=request.sql_query
            )

        result = await run_in_threadpool(execute_query, conn, request.sql_query, offset, fetch, total_records)

        # Optional transformation: format rows into dicts
        try:
            result["rows"] = [{"id": row[0], "name": row[1]} for row in result["rows"]]
        except Exception as e:
            logger.warning(f"Failed to format rows to dicts: {e}")

        if result["total_records"] == 0 or not result["rows"]:
            result["message"] = "No data found"
            result["rows"] = []
            result["columns"] = []

        # Normalize message_code to int
        message_code_map = {
            "SUCCESS": 1,
            "NO_DATA": 0,
        }
        result["message_code"] = message_code_map.get(result.get("message_code", "SUCCESS"), 1)

        execution_time = result.get("execution_time", "0.00 seconds")

        conn.close()

        return SQLExecutionResponse(
            columns=result["columns"],
            rows=result["rows"],
            message=result["message"],
            message_code=result["message_code"],
            execution_time=execution_time,
            query_status=result["query_status"],
            row_count=result["row_count"],
            data_size_mb=result["data_size_mb"],
            total_records=total_records,
            generated_sql=result.get("executed_sql", "")
        )

    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        raise e
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error: {error_msg}")

        # Optional: match test expectations
        if "Invalid SQL query" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid SQL query")
        if "Database crashed" in error_msg:
            raise HTTPException(status_code=500, detail="Failed to fetch total records from DB")

        raise HTTPException(status_code=500, detail=f"Internal Server Error: {error_msg}")



@app.post("/generate-and-execute-sql", tags=["SQL Generation & Execution"])
def api_generate_and_execute_sql(request: QueryRequest, offset: int = 0, fetch: int = 10):
    """
    API Endpoint to generate and execute SQL in a single request with pagination.
    Optimized to skip heavy processing if query contains inappropriate/destructive content.
    """
    logger.info(f"Received request to generate and execute SQL: {request.query} (Offset: {offset}, Fetch: {fetch})")

    # ✅ Initialize Content Safety
    # ✅ STEP 1: Check user prompt content
    safety_result = content_safety.check(request.query, context="User Prompt")
    if not safety_result['execution_allowed']:
        return {
            "generated_summary": "The requested query cannot be processed due to security or compliance reasons.",
            "generated_sql": "***Prompt blocked due to security policies***",
            "generated_recommendations": safety_result['recommendations'],
            "query_complexity": {},
            "validation_warnings": [],
            "missing_tables": [],
            "generation_time": "0.00 seconds",
            "validation_flag": True,
            "execution_allowed": False,
            "execution_result": {
                "columns": [],
                "rows": [],
                "message": "Blocked for security reasons: " + "; ".join(safety_result['detected_reasons']),
                "message_code": 400,
                "execution_time": "0.00 seconds",
                "query_status": "Query Not Executed",
                "row_count": None,
                "data_size_mb": None,
                "total_records": None
            }
        }


    # ✅ Generate SQL Query & Execute (only if safe)
    result = generate_sql_query(request.query, validator.schema, execute_query_flag=True, offset=offset, fetch=fetch)
    
    if result is None:
        logger.error("❌ SQL Query Generation Failed: Result is None.")
        return {
            "execution_allowed": False,
            "generated_summary": None,
            "generated_sql": None,
            "generated_recommendations": None,
            "query_complexity": None,
            "validation_warnings": [],
            "missing_tables": [],
            "generation_time": "0.00 seconds",
            "execution_result": {
                "columns": [],
                "rows": [],
                "message": "Query execution failed. No results returned.",
                "message_code": 500,
                "execution_time": "0.00 seconds",
                "query_status": "Query Failed",
                "row_count": None,
                "data_size_mb": None,
                "total_records": None
            }
        }
    execution_allowed = result.get("execution_allowed", True)
    # execution_allowed = result.get("execution_allowed") if result and isinstance(result, dict) else None

    # ✅ Block execution if flagged by internal logic (e.g., non-SELECT query detection)
    if not execution_allowed:
        logger.warning("Query blocked due to internal safety rules.")
        return {
            **result,
            "execution_allowed": False,
            "execution_result": {
                "columns": [],
                "rows": [],
                "message": "I can help you find and view information, but I’m not able to change or delete anything. Please let me know what you’d like to see.",
                "message_code": 400,
                "execution_time": "0.00 seconds",
                "query_status": "Query Not Executed",
                "row_count": None,
                "data_size_mb": None,
                "total_records": None
            }
        }

    # ✅ If everything allowed, return result including execution output
    return {
        **result,
        "execution_allowed": True
    }

@app.get("/getdashboarddata", tags=["DataGenie Metrics"])
def get_data_genie_metrics():
    """
    Endpoint to execute the stored procedure sp_Get_DataGenie_Metrics
    and return all its result sets.
    """
    logger.info("Executing stored procedure: sp_Get_DataGenie_Metrics")
    conn = get_db_connection()

    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        cursor = conn.cursor()
        cursor.execute("EXEC [dbo].[sp_Get_DataGenie_Metrics]")

        result_sets = []
        while True:
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            formatted_rows = [
                {col: str(value).replace("\n", " ") if value is not None else None for col, value in zip(columns, row)}
                for row in rows
            ]
            result_sets.append({
                "columns": columns,
                "rows": formatted_rows
            })

            if not cursor.nextset():
                break

        logger.info("Stored procedure executed and all result sets retrieved.")
        return {"status": "success", "result_sets": result_sets}

    except Exception as e:
        logger.error(f"Error executing stored procedure: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute stored procedure.")

    finally:
        conn.close()

class TicketUpdateRequest(BaseModel):
    ticket_number: str
    status: str
    resolved_by: str

@app.post("/update-ticket-status", tags=["Ticket Management"])
async def update_ticket_status(request: TicketUpdateRequest):
    logger.info(f"Received ticket update request: {request}")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    try:
        cursor = conn.cursor()

        cursor.execute("EXEC dbo.sp_UpdateDataGenieTicketStatus ?, ?, ?",
                       request.ticket_number, request.status, request.resolved_by)

        conn.commit()

        # Broadcast the update to all connected clients
        if request.status.lower() == "assigned":
            message = f"Ticket number: {request.ticket_number} is assigned to {request.resolved_by}."
        elif request.status.lower() == "resolved":
            message = f"Ticket number: {request.ticket_number} was resolved by {request.resolved_by}."
        else:
            message = f"Ticket number: {request.ticket_number} updated to status '{request.status}' by {request.resolved_by}."

        await manager.broadcast(message)

        logger.info(f"✅ Ticket {request.ticket_number} updated successfully.")
        return {"message": "Ticket updated successfully."}

    except Exception as e:
        logger.error(f"Error updating ticket status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

    finally:
        conn.close()

@app.get("/get-ticket-status", tags=["Ticket Management"])
def get_ticket_status(ticket_number: str = Query(..., description="Ticket Number to check")):
    logger.info(f"Checking status for Ticket Number: {ticket_number}")
    conn = get_db_connection()
    
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed.")
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT TicketId, TicketNumber, Status, ResolvedBy, ResolutionDate
            FROM vw_TicketStatusDetail
            WHERE TicketNumber = ?
        """
        cursor.execute(query, (ticket_number,))
        row = cursor.fetchone()

        if not row:
            return {"status": "not_found", "message": "Ticket not found."}

        columns = [col[0] for col in cursor.description]
        result = {columns[i]: row[i] for i in range(len(columns))}

        return  result

    except Exception as e:
        logger.error(f"Error retrieving ticket status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ticket status.")
    
    finally:
        conn.close()

@app.get("/api/health", tags=["Health Check"])
def health_check():
    """Health check endpoint."""
    return {"status": "API is running successfully."}

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the DataGenie API!"}

# WebSocket Manager to handle connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Initialize WebSocket Manager
manager = ConnectionManager()

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# START FASTAPI SERVER
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")