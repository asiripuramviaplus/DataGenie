import json
import re
import os
import time
#import logging
#import ollama
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from logger_config import logger  # Import centralized logger
import configparser

# # Configure logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)
# ✅ Load Azure API details from config.inf
config = configparser.ConfigParser()
config.read("config.inf")


AZURE_OPENAI_ENDPOINT = config.get("AZURE", "ENDPOINT")
AZURE_OPENAI_API_KEY = config.get("AZURE", "API_KEY")
AZURE_OPENAI_DEPLOYMENT = config.get("AZURE", "DEPLOYMENT")
AZURE_OPENAI_API_VERSION = config.get("AZURE", "API_VERSION")

# Load schema dynamically

with open("schema_template.json", "r", encoding="utf-8") as schema_file:

    schema_text = json.load(schema_file)

# Summarize schema for LLM context
schema_summary = "\n".join([f"Table: {k}, Description: {v['Description']}" for k, v in schema_text.items()])

# ✅ Initialize Azure AI Client
azure_model = ChatCompletionsClient(
    endpoint=f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/?{AZURE_OPENAI_API_VERSION}",
    credential=AzureKeyCredential(AZURE_OPENAI_API_KEY),
)

# Global variables for context persistence
CHAT_HISTORY = []
LAST_INTENT = None

def extract_optimized_schema(entity_input):
    optimized_schema = {}

    # Handle both list and comma-separated string
    if isinstance(entity_input, str):
        entity_list = [e.strip() for e in entity_input.split(',')]
    elif isinstance(entity_input, list):
        entity_list = [e.strip() for e in entity_input]
    else:
        print("❌ Invalid entity input type")
        return "{}"

    for entity in entity_list:
        normalized_entity = f"Table: {entity}"
        if normalized_entity in schema_text:
            table_info = schema_text[normalized_entity]

            # Build column details with optional descriptions
            columns_with_descriptions = []
            for col in table_info["Columns"]:
                col_info = {
                    "Column": col["Column"],
                    "DataType": col["DataType"]
                }
                if "Description" in col and col["Description"]:
                    col_info["Description"] = col["Description"]
                columns_with_descriptions.append(col_info)

            optimized_schema[normalized_entity] = {
                "Description": table_info["Description"],
                "Columns": columns_with_descriptions,
                "RowCount": table_info["RowCount"],
                "MasterDataValues": table_info["MasterDataValues"]
            }
        else:
            print(f"❌ No schema found for entity: {entity} (looked for {normalized_entity})")

    return json.dumps(optimized_schema, indent=4) if optimized_schema else "{}"




# Function to extract intent using Azure OpenAI
def extract_intent_azure(question: str):
    system_message = (
        f"You are an AI assistant specialized in Mobility Platform data queries. "
        f"Users are non-technical and ask questions in natural language.\n\n"
        f"Your primary job is to extract structured intent (action, entity, filters) from user queries related to data.\n\n"
        f"entity should be accurately named after table name letter to letter"
        f"If the user's question is outside the context Mobility Platform schema and outside the schema, "
        f"respond with this JSON format : {{ \"summary\": \"The request does not align with the supported Mobility Platform schema\", \"Query not generated as the request is out of the defined schema context\": \"no query generated\", \"recommendations\": \"This tool is designed to convert natural language statements into SQL queries based on the Mobility Platform schema. Please ensure your question is within the supported context.\" }}"
        f"Perform a content safety check for inappropriate, PII, or dangerous SQL content.\n\n"
        f"Your job is to Extract structured 'action', 'entity', and 'filters' based on the user's query.\n"
        f"- Understand and use the following schema to identify entities:\n\n"
        f"{schema_summary}\n\n"
        f"Format your answer as JSON with keys: action, entity, filters.\n\n"
        f"Example format:\n"
        f"{{\n"
        f'  "action": "list",\n'
        f'  "entity": "payments",\n'
        f'  "filters": "March 2023, Habitual Violators"\n'
        f'  "sql_keywords": "TOP, JOIN, GROUP BY, ORDER BY, etc. as needed for query structure)"\n'
        f"}}"
    )

    logger.info("User Query is supplied to Azure Intent Agent for processing.")
    user_prompt = f"User Query: {question}\n\nRespond in the specified JSON format only."

    try:
        response = azure_model.complete(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
        )

        print(f"📤 Raw Azure API Response: {response}")  # Debugging
        content = response.choices[0].message.content.strip().strip("```json").strip("```")
        print(f"📜 Extracted JSON Content: {content}")  # Debugging
        logger.info(f"Raw Azure LLM Response:\n{content}")

        intent = json.loads(content)
        entity = intent.get("entity")
        #print(f"🎯 Extracted Intent: {intent}")  # Debugging

        # Fetch and add optimized schema if entity exists
        intent["optimized_schema"] = extract_optimized_schema(entity) if entity else "{}"
        #print(f"🔄 Final Intent with Schema: {intent}")  # Debugging

        return json.dumps(intent, indent=4)
    

    except json.JSONDecodeError:
        logger.info(f"[ERROR] Failed to parse Azure LLM response as JSON.")
        return {"error": "Invalid JSON response", "raw": content}
    except Exception as e:
        logger.info(f"[ERROR] Exception during Azure LLM call: {e}")
        return {"error": str(e)}

# Function to extract intent using Mistral (Ollama)
def extract_intent_mistral(question: str):
    system_prompt = (
        f"You are an AI assistant specialized in Mobility Platform data queries. "
        f"Users are non-technical and ask questions in natural language.\n\n"
        f"Your primary job is to extract structured intent (action, entity, filters) from user queries related to data.\n\n"
        f"entity should be accurately named after table name  from schema_summary letter to letter"
        f"If the user's question is unrelated to data queries, SQL translation, or the Mobility Platform schema, "
        f"Perform a content safety check for inappropriate, PII, or dangerous SQL content.\n\n"
        f"Your job is to Extract structured 'action', 'entity', and 'filters' based on the user's query.\n"
        f"- Understand and use the following schema to identify entities:\n\n"
        f"{schema_summary}\n\n"
        f"Format your answer as JSON with keys: action, entity, filters.\n\n"
        f'User Query: {question}\n\n'
        f'The extracted entity **must match the schema exactly**, including prefixes like `REPORTS.`.\n'
        f'DO NOT shorten or modify table names.\n'
        f'Extract the entity name **only after "Table: ** from the schema template.\n'
        f"Example format:\n"
        f"{{\n"
        f'  "action": "list",\n'
        f'  "entity": "payments",\n'
        f'  "filters": "March 2023, Habitual Violators"\n'
        f"}}"
    )

# Main function to switch between Azure and Mistral based on flag
def extract_intent(question: str, flag: int):
    global CHAT_HISTORY, LAST_INTENT

    
    if flag == 1:
        intent = extract_intent_azure(question)
    else:
        intent = extract_intent_mistral(question)
    
    # Parse the intent JSON
    try:
        if isinstance(intent, str):
            intent = json.loads(intent)
    except json.JSONDecodeError:
        logger.error("Failed to parse intent JSON.")
        return {"error": "Invalid intent format", "raw": intent}

    # Get the current intent's action and entity
    current_intent = {
        "action": intent.get("action"),
        "entity": intent.get("entity"),
        "filters": intent.get("filters"),
        "sql_keywords": intent.get("sql_keywords"),
        "optimized_schema": intent.get("optimized_schema")
    }
    logger.info(f"Extracted current intent: {current_intent}")

    if not current_intent["action"] or not current_intent["entity"]:
        
        if LAST_INTENT is None:
            logger.error("No previous intent available to reuse.")
            return {"error": "No intent generated and no previous intent available."}

        # If intent is not generated, reuse the previous intent
        logger.warning("Intent not generated. Reusing the previous intent.")
        current_intent = LAST_INTENT
        intent["action"] = LAST_INTENT["action"]
        intent["entity"] = LAST_INTENT["entity"]
        intent["filters"]=LAST_INTENT["filters"]
        intent["sql_keywords"]=LAST_INTENT["sql_keywords"]
        intent["optimized_schema"]=LAST_INTENT["optimized_schema"]
        logger.info(f"Reused LAST_INTENT: {LAST_INTENT}")
    else:
        # If intent is generated, update LAST_INTENT
        if (LAST_INTENT!=current_intent):
            CHAT_HISTORY = []
            logger.info(f"Chat history cleared. New context started: {CHAT_HISTORY}")
            
        LAST_INTENT = current_intent
        logger.info(f"Updated LAST_INTENT: {LAST_INTENT}")
        
    # Check if the current intent matches the last intent

    if LAST_INTENT == current_intent:
        CHAT_HISTORY.append(question)
        logger.info(f"Appended to CHAT_HISTORY: {CHAT_HISTORY}")
    else:
        CHAT_HISTORY = [question]
        logger.info(f"Chat history cleared. New context started: {CHAT_HISTORY}")

    # Add the chat history to the intent for context
    intent["chat_history"] = CHAT_HISTORY
    logger.debug(f"Final intent with chat history: {intent}")
    return intent


    


# Example Test Run
if __name__ == "__main__":
    flag = 1 # Change to 0 to use Mistral
    # user_query = "ok list them"
    # result = extract_intent(user_query, flag)
    # print("\n✅ Extracted Intent:\n", json.dumps(result, indent=4))
    while True:
        user_query = input("Enter your query (or type 'exit' to quit): ").strip()
        if user_query.lower() == "exit":
            print("Exiting...")
            break

        # Extract intent and handle context
        result = extract_intent(user_query, flag)
        print("\n✅ Extracted Intent:\n", json.dumps(result, indent=4))