import re
# import logging
from logger_config import logger  # Import centralized logger
# logger = logging.getLogger(__name__)

class ContentSafetyChecker:
    """
    Class to handle all Content Safety, PII detection, and SQL safety checks.
    """

    def __init__(self):
        self.inappropriate_keywords = [
            "sex", "violence", "drugs", "gambling", "adult", "XXX", "porn", "explicit", "nude", "erotic"
        ]
        self.pii_keywords = [
            "ssn", "social security number", "credit card", "cvv", "pin", "password", "dob", "birthdate", "email", "phone"
        ]
        self.dangerous_sql_keywords = [
            "drop", "delete", "truncate", "alter", "insert", "update", "create", "exec", "merge"
        ]

    def check(self, text: str, context: str = "Unknown") -> dict:
        """
        Perform complete content safety check and return structured dict including
        execution_allowed, reasons, and context-specific recommendations.
        """
        detected_reasons = []
        detected_types = set()  # Track what type of violation detected

        for keyword in self.inappropriate_keywords:
            if re.search(rf"\b{keyword}\b", text, re.IGNORECASE):
                detected_reasons.append(f"Inappropriate content detected: {keyword}")
                detected_types.add("inappropriate")

        for keyword in self.pii_keywords:
            if re.search(rf"\b{keyword}\b", text, re.IGNORECASE):
                detected_reasons.append(f"PII content detected: {keyword}")
                detected_types.add("pii")

        for keyword in self.dangerous_sql_keywords:
            if re.search(rf"\b{keyword}\b", text, re.IGNORECASE):
                detected_reasons.append(f"SQL operation detected: {keyword}")
                detected_types.add("dangerous_sql")

        execution_allowed = False if detected_reasons else True

        if not execution_allowed:
            logger.warning(f"[Content Safety Blocked] {context}: {', '.join(detected_reasons)}")
        else:
            logger.info(f"[Content Safety Passed] {context}")

        # Generate context-sensitive recommendations
        recommendations = self._generate_recommendations(detected_types)

        return {
            "execution_allowed": execution_allowed,
            "detected_reasons": detected_reasons,
            "context": context,
            "recommendations": recommendations
        }

    def _generate_recommendations(self, detected_types: set) -> list:
        """Generate contextual recommendations based on detected issues."""
        recs = []
        if "inappropriate" in detected_types or "pii" in detected_types:
            recs.append("Please avoid using sensitive, inappropriate, or confidential content in your query.")
        if "dangerous_sql" in detected_types:
            recs.append("Modifying data through DELETE, DROP, TRUNCATE, UPDATE, or INSERT is restricted. Focus on reading or viewing data.")
        if not recs:  # Default catch-all
            recs.append("Ensure your query aligns with business and security policies.")
        return recs
