import sqlparse
import difflib
import json
#import logging
import re
from logger_config import logger 

# ✅ Load Schema from JSON
def load_schema(schema_path):
    """Load schema information from a JSON file."""
    logger.info(f"Loading schema from {schema_path}...")
    try:
        with open(schema_path, "r", encoding="utf-8") as file:
            schema_info = json.load(file)
        logger.info("Schema loaded successfully.")
        return schema_info
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        return None

# ✅ Improved Parentheses Validator (Avoid False Positives)
def is_balanced_parentheses(query):
    """Check if SQL query has balanced parentheses using a stack approach."""
    stack = []
    for char in query:
        if char == "(":
            stack.append("(")
        elif char == ")":
            if not stack:
                return False  # Unmatched closing parenthesis
            stack.pop()
    return not stack  # True if stack is empty (balanced), False if unbalanced

# ✅ Validate SQL Syntax (Without Executing on DB)
def validate_sql_syntax(query):
    """Check SQL syntax using sqlparse without database execution."""
    try:
        query = sqlparse.format(query.strip(), reindent=True, keyword_case="upper")  # Format query

        # ✅ Check for unbalanced parentheses using stack-based validation
        if not is_balanced_parentheses(query):
            return False, "Syntax error: Unbalanced parentheses detected."

        # ✅ Check if SQL starts with SELECT
        if not re.match(r"^\s*SELECT\b", query, re.IGNORECASE):
            return False, "Syntax error: Missing SELECT statement."

        # ✅ Ensure WHERE clause is present in DELETE/UPDATE (Security Check)
        if re.search(r"\bDELETE\b|\bUPDATE\b", query, re.IGNORECASE) and "WHERE" not in query.upper():
            return False, "Unsafe SQL: WHERE clause missing in DELETE/UPDATE statement."

        return True, "SQL syntax is valid."
    except Exception as e:
        return False, f"Syntax validation error: {e}"

# ✅ Auto-Correct SQL Query Based on Schema
def correct_sql_query(query, schema_info):
    """Correct common issues in SQL queries like table/column names."""
    query = sqlparse.format(query.strip(), reindent=True, keyword_case="upper")  # Standardize format

    for table, details in schema_info.items():
        table_name = table.split(".")[-1]  # Extract table name
        if table_name.lower() in query.lower():
            query = query.replace(table_name, table)  # Correct table name

            for column in details.get("Columns", []):
                column_name = column["Column"]
                matches = difflib.get_close_matches(column_name, query.split(), n=1, cutoff=0.8)
                if matches:
                    query = query.replace(matches[0], column_name)  # Correct column names

    return query

# ✅ Validate & Auto-Correct SQL
def validate_and_correct_sql(query, schema_path):
    """Validate SQL syntax and auto-correct issues based on schema JSON."""
    schema_info = load_schema(schema_path)
    if not schema_info:
        return None, "Schema loading failed."

    valid, message = validate_sql_syntax(query)
    if valid:
        logger.info("✅ SQL is valid!")
        return query, "SQL is valid."

    logger.warning(f"⚠️ SQL Syntax Issue: {message}")
    corrected_query = correct_sql_query(query, schema_info)
    valid, message = validate_sql_syntax(corrected_query)

    if valid:
        logger.info("✅ SQL corrected successfully!")
        return corrected_query, "SQL corrected successfully."
    else:
        logger.error("❌ Could not auto-correct SQL. Manual review required.")
        return None, "Auto-correction failed."

# ✅ Test Case
if __name__ == "__main__":
    test_query = """
    SELECT SNO, AFFIDAVITCREATEDDATE, AFFIDAVITTYPE, REQUESTEDSTATUS, LOCATIONCODE, CNT, 
           TOLLCNT, TOLLAMOUNT, INVOICECNT, INVOICEAMT, CREATEDDATE, CREATEDBY, UPDATEDDATE, UPDATEDBY 
    FROM PBI.DISPUTES_SUMMARY_V2 
    WHERE AFFIDAVITCREATEDDATE >= DATEADD(WEEK, -1, CAST(GETDATE() AS DATE)) 
    AND AFFIDAVITCREATEDDATE < CAST(GETDATE() AS DATE));
    """

    schema_path = "schema_template.json"
    corrected_query, message = validate_and_correct_sql(test_query, schema_path)
    print("\n🔹 Corrected SQL Query:\n", corrected_query)