import json
#import logging
from logger_config import logger 
# Configure logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)

class TableValidator:
    def __init__(self, schema_path):
        """Initialize Table Validator by loading schema JSON"""
        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.table_info = self._extract_table_info()
        self.large_table_threshold = 500000  # ✅ Define row count threshold for large tables

    def _load_schema(self):
        """Load schema JSON file."""
        try:
            with open(self.schema_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"❌ Error loading schema file: {e}")
            return {}

    def _extract_table_info(self):
        """Extract table names and row counts from schema."""
        table_info = {}
        for table_name, details in self.schema.items():
            row_count = details.get("RowCount", 0)
            table_info[table_name] = {
                "description": details.get("Description", "No description available."),
                "row_count": row_count
            }
        return table_info

    def validate_tables(self, tables_received):
        """Validate tables against schema and suggest optimizations."""
        missing_tables = []
        optimization_recommendations = []

        for table in tables_received:
            if table not in self.table_info:
                missing_tables.append(table)
            else:
                row_count = self.table_info[table]["row_count"]
                if row_count > self.large_table_threshold:
                    optimization_recommendations.append(
                        f"⚠️ The table `{table}` contains {row_count:,} records. "
                        f"Consider applying filters such as date range, status, or limiting results for better performance."
                    )

        return {
            "missing_tables": missing_tables,
            "optimization_suggestions": optimization_recommendations,
            "validation_flag": bool(optimization_recommendations)  # ✅ Set validation flag if optimizations exist
        }