from langchain.llms import CTransformers
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


class LlamaRecommendationEngine:
    def __init__(self, model_path: str):
        """
        Initialize the LLaMA model via ctransformers for local recommendation generation.
        :param model_path: Path to the local LLaMA model file.
        """
        self.llm = CTransformers(
            model=model_path,
            model_type="llama",
            config={'max_new_tokens': 512, 'temperature': 0.5}
        )

        self.prompt_template = PromptTemplate(
            input_variables=["sql_query", "total_records", "schema_info"],
            template="""
            You are an expert SQL and data advisor. Given the following SQL query, its estimated total record count, and the database schema information, provide smart, user-friendly recommendations to improve the performance, efficiency, and usability of the query. 
            Avoid using technical jargon, and instead focus on suggestions that can help end-users get better, faster, and more relevant data.
            
            SQL Query:
            {sql_query}

            Estimated Total Records: {total_records}

            Database Schema Info:
            {schema_info}

            Recommendations:
            """
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)

    def generate_recommendations(self, sql_query: str, total_records: int, schema_info: str) -> str:
        """
        Generate recommendations based on SQL query, total records, and schema info.
        :param sql_query: The generated SQL query.
        :param total_records: Estimated total record count from the query.
        :param schema_info: JSON or string format of database schema.
        :return: Natural language recommendations as string.
        """
        try:
            result = self.chain.run({
                "sql_query": sql_query,
                "total_records": total_records,
                "schema_info": schema_info
            })
            return result.strip()
        except Exception as e:
            return f"Failed to generate recommendations: {e}"
