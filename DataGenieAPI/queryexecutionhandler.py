import sqlparse
import logging
import json
import pyodbc
import difflib
import re
from sqlvalidator import validate_sql_syntax
from TableValidator import TableValidator
from sqlquerygenerator import connect_to_database, db_config
from sqlquerygenerator import   load_schema_from_json, schema_json_path
from logger_config import logger

SCHEMA_JSON_PATH = load_schema_from_json(schema_json_path)
# logger.info(f"Extracted tables: {SCHEMA_JSON_PATH}")

# Initialize Table Validator
table_validator = TableValidator(SCHEMA_JSON_PATH)

# Restricted SQL patterns (to prevent destructive queries)
RESTRICTED_PATTERNS = [
    r"DROP\s+TABLE", r"DELETE\s+FROM\s+\w+", r"ALTER\s+TABLE",
    r"TRUNCATE\s+TABLE", r"INSERT\s+INTO\s+\w+", r"UPDATE\s+\w+\s+SET"
]

# ✅ Validate SQL Query
def validate_sql_query(query):
    """Validates an SQL query for syntax, security, and correctness."""
    query = sqlparse.format(query.strip(), reindent=True, keyword_case="upper")

    # Check syntax
    is_valid, validation_msg = validate_sql_syntax(query)
    if not is_valid:
        return False, f"❌ Invalid SQL syntax: {validation_msg}"

    # Check for restricted patterns
    for pattern in RESTRICTED_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return False, f"❌ Query contains restricted operations: {pattern}"

    # Extract tables and validate against schema
    tables_in_query = extract_tables_from_sql(query)
    validation_result = table_validator.validate_tables(tables_in_query)
    # Convert schema tables to lowercase for comparison
    schema_tables = {table.lower() for table in table_validator.schema.keys()}
    extracted_tables = extract_tables_from_sql(query)

    # Normalize schema-prefixed table names for validation
    normalized_tables = set()
    for table in extracted_tables:
        if "." not in table:  # If schema is missing, assume `dbo.`
            normalized_tables.add(f"dbo.{table}".lower())
        else:
            normalized_tables.add(table.lower())

    missing_tables = [table for table in normalized_tables if table not in schema_tables]

    if missing_tables:
        return False, f"❌ Missing tables: {', '.join(missing_tables)}"

        if validation_result["optimization_suggestions"]:
            return False, f"⚠️ Optimization needed: {', '.join(validation_result['optimization_suggestions'])}"

        return True, "✅ SQL query is valid."

# ✅ Extract Tables from SQL
def extract_tables_from_sql(query):
    """Extracts fully qualified table names (schema + table) from SQL query using sqlparse."""
    parsed = sqlparse.parse(query)
    tables = set()

    for statement in parsed:
        from_seen = False
        for token in statement.tokens:
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() in ("FROM", "JOIN"):
                from_seen = True
            elif from_seen and isinstance(token, sqlparse.sql.Identifier):
                table_name = token.get_real_name()
                schema_name = token.get_parent_name()  # Extract schema if available
                full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
                tables.add(full_table_name.lower())  # Normalize case
                from_seen = False
            elif from_seen and isinstance(token, sqlparse.sql.IdentifierList):
                for identifier in token.get_identifiers():
                    table_name = identifier.get_real_name()
                    schema_name = identifier.get_parent_name()
                    full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
                    tables.add(full_table_name.lower())
                from_seen = False

    return tables


# ✅ Execute Query Safely
def execute_safe_query(query):
    """Executes a validated SQL query safely."""
    # Validate SQL before execution
    is_valid, validation_msg = validate_sql_query(query)
    if not is_valid:
        return {"error": validation_msg}

    conn = connect_to_database(db_config)
    if not conn:
        return {"error": "Database connection failed."}

    try:
        cursor = conn.cursor()
        cursor.execute(query)

        # Fetch columns
        columns = [desc[0] for desc in cursor.description]

        # Fetch results (limit to avoid large queries)
        rows = cursor.fetchmany(1000)

        # Convert rows to JSON-friendly format
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "columns": columns,
            "rows": results,
            "message": "✅ Query executed successfully.",
            "query_status": "Success"
        }

    except pyodbc.ProgrammingError as e:
        return {"error": f"SQL Execution Error: {str(e)}"}
    finally:
        conn.close()

# ✅ Query Feedback Loop
def refine_query_with_feedback(query, feedback):
    """Refines an SQL query based on user feedback."""
    logger.info(f"Refining query based on feedback: {feedback}")

    # Example: If user asks to add a filter
    if "add filter" in feedback.lower():
        query = query + " WHERE created_date >= DATEADD(MONTH, -1, GETDATE())"

    return query

# ✅ Test Function
if __name__ == "__main__":
    test_query = "SELECT * FROM employees WHERE department = 'Sales'"
    
    print("\n🔹 Validating Query...")
    valid, msg = validate_sql_query(test_query)
    print(msg)

    if valid:
        print("\n🔹 Executing Query...")
        execution_result = execute_safe_query(test_query)
        print(json.dumps(execution_result, indent=2))

        print("\n🔹 Refining Query Based on Feedback...")
        refined_query = refine_query_with_feedback(test_query, "Add filter for recent records")
        print("Updated Query:", refined_query)
