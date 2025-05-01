import pyodbc
import logging
from db_connection import get_db_connection

class SQLQueryCache:
    """Class to check if a similar query already exists in the database and reuse it."""
    
    def __init__(self):
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor() if self.conn else None

    def check_existing_query(self, prompt):
        """Check if the given prompt already exists in the audit log."""
        if not self.cursor:
            logging.warning("Database connection is not available.")
            return None

        try:
            normalized_prompt = prompt.strip().lower()
            logging.info(f"Checking for existing query for prompt: {normalized_prompt}")

            query ="exec [dbo].[sp_Get_CachedAuditByPrompt] @Prompt = ?"
             # ✅ Log the formatted query with actual prompt
            formatted_query = query.replace("?", f"'{normalized_prompt}'")
            logging.info(f"Query executed----?: {formatted_query}")

            self.cursor.execute(formatted_query)
            result = self.cursor.fetchone()
            logging.info(f"Query result-->: {result}")

            if result:
                logging.info("✅ An existing SQL query was retrieved from cache. Skipping regeneration.")
                return {
                    "auditid": result[0],
                    "IsReusedPrompt": 1,
                    "generated_sql": result[2],
                    "generated_summary": result[3],
                    "generated_recommendations": result[4],
                    "query_complexity": result[5],
                    "generated_intent": result[6]
                }
            else:
                logging.info("❌ No existing entry found for this query in the cache.")
                return None
        except pyodbc.Error as e:
            logging.error(f"❌ Database error: {e}")
            return None

    def close_connection(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()