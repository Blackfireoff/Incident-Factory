# services/bedrock_service.py

import boto3
import json
import os
import re
from typing import List, Dict, Any, Literal

MODEL_ID = "arn:aws:bedrock:us-east-1:010526273152:inference-profile/us.meta.llama3-2-11b-instruct-v1:0" 
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

class BedrockService:
    
    def __init__(self, region_name: str = AWS_REGION):
        try:
            self.bedrock = boto3.client(
                service_name="bedrock-runtime", 
                region_name=region_name
            )
        except Exception as e:
            print("Error: Could not initialize Boto3 Bedrock client.")
            raise Exception(f"Bedrock client error: {e}")

    def _call_bedrock(self, system_prompt: str, user_content: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
        """Helper function to call the Bedrock converse API."""
        try:
            response = self.bedrock.converse(
                modelId=MODEL_ID,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user", 
                        "content": [{"text": user_content}]
                    }
                ],
                inferenceConfig={
                    "temperature": temperature,
                    "maxTokens": max_tokens
                }
            )
            return response["output"]["message"]["content"][0]["text"]

        except Exception as e:
            print(f"Error during Bedrock call (converse): {e}")
            if "AccessDeniedException" in str(e):
                print(f"Error: Access denied. Have you requested access to model '{MODEL_ID}' in the Bedrock console?")
            raise e 

    def decide_tool(self, user_query: str) -> Literal["sql", "search"]:
        """
        Decides which tool to use (SQL or RAG/Semantic Search).
        """
        system_prompt = f"""
        You are an intelligent routing agent. Your purpose is to decide which tool to use to answer the user's question.
        You have two choices:
        1.  "sql": Use this tool for questions requiring counting, listing, aggregating, or filtering structured data (e.g., "How many...", "List all incidents at...", "Give me the top 5...", "Generate a graph...").
        2.  "search": Use this tool for open-ended, semantic, or reasoning questions (e.g., "Why...", "How to prevent...", "What happened...", "What incidents involve stairs...").

        Routing Examples:
        -   Question: "Affiche tous les événements du dernier mois en Abitibi" -> "sql"
        -   Question: "Quels événements impliquent des escaliers par temps froid?" -> "search"
        -   Question: "Liste toutes les blessures qui auraient pu être évitées avec un casque" -> "search"
        -   Question: "Quels types de machines sont impliquées dans le plus de blessures ?" -> "sql"
        -   Question: "Propose un plan d'action pour réduire la gravité..." -> "search"

        Respond ONLY with "sql" or "search". Do not say anything else.
        """
        
        response = self._call_bedrock(
            system_prompt=system_prompt, 
            user_content=user_query, 
            temperature=0.0, 
            max_tokens=10
        )
        
        if "sql" in response.lower():
            return "sql"
        return "search"

    # --- FUNCTION generate_sql_query (PROMPT UPDATED) ---
    def generate_sql_query(self, schema: str, user_query: str) -> str:
        """
        Generates a SQL query from the user's question and the schema.
        """
        system_prompt = f"""
        You are a PostgreSQL expert. Given the database schema below, write a single, efficient, and readable SELECT query to answer the user's question.
        -   Return ONLY the SQL query, with no explanations, comments, or markdown (like ```sql).
        
        --- STRICT RULES ---
        1.  **One Query:** You MUST generate *one and only one* SELECT query. Do NOT use `WITH ... AS` (Common Table Expressions), do not use semicolons (`;`), and do not write multiple separate `SELECT` statements.
        
        2.  **"Gravest" interpretation:** To interpret "the gravest" or "most severe", use the `risk.gravity` column (Hints: 'Low', 'Medium', 'High', 'Critical').
            -   *Example logic:* "the most severe" -> `WHERE r.gravity = 'CRITICAL'`

        3.  **Obey Hints:** The 'Value Hints' (e.g., 'INJURY') ARE the single source of truth. You MUST use them.
        
        4.  **Use IDs:** If the user's question mentions a specific ID (e.g., "incident 83"), you MUST use that numeric ID in your `WHERE` clause. Do NOT add other text filters. The ID is sufficient and takes priority.
        
        5.  **Respect Joins:** You MUST NOT invent columns. To link `event` and `corrective_measure`, you MUST use the `event_corrective_measure` junction table.
        
        6.  **COUNT Context:** If the question asks for a simple 'COUNT', preserve the context (e.g., `SELECT type, COUNT(*) ... GROUP BY type`).

        7.  **"Declared By" Definition:** A question about who "declared" or "reported" an incident refers to `event.declared_by_id`.

        8.  **[NEW RULE] "Involved" vs. "Declared":** The `event_employee` table lists employees *involved* in the incident (e.g., witness, victim). This is different from `event.declared_by_id` (the reporter).
            -   *Query "who was involved":* `... JOIN event_employee ee ON e.event_id = ee.event_id JOIN person p ON ee.person_id = p.person_id`
            -   *Query "who reported":* `... JOIN person p ON e.declared_by_id = p.person_id`

        9.  **[WAS RULE 8] Uppercase Matching:** When filtering text values for the columns `gravity`, `type`, `classification`, `probability`, or `matricule`, you MUST use uppercase.
            -   *Correct:* `WHERE classification = 'INJURY'`
            -   *Correct:* `WHERE r.gravity = 'CRITICAL'`
        --- END OF RULES ---

        --- SCHEMA ---
        {schema}
        --- END SCHEMA ---
        """
        
        response = self._call_bedrock(
            system_prompt=system_prompt, 
            user_content=user_query, 
            temperature=0.0, 
            max_tokens=1024
        )
        
        # Nettoyer la réponse pour ne garder que le SQL
        sql_query = response.strip()
        if "```sql" in sql_query:
            match = re.search(r"```sql\n(.*?)\n```", sql_query, re.DOTALL | re.IGNORECASE)
            if match:
                sql_query = match.group(1)
        
        if not sql_query.upper().startswith("SELECT"):
             select_index = sql_query.upper().find("SELECT")
             if select_index != -1:
                 sql_query = sql_query[select_index:]
             
        return sql_query.strip().replace(";", "")

    # --- FONCTION generate_rag_response (Refonte Totale du Prompt) ---
    def generate_rag_response(self, context: str, user_query: str) -> str:
        """
        Generates a natural language response based on a context (RAG or SQL).
        """
        
        base_prompt = """
        You are an expert AI assistant for analyzing safety and environmental incidents.
        Your goal is to answer the user's question based on the facts in the provided context.
        You MUST **NEVER** mention that you are basing your answer on "the context" or "the provided information." Answer directly.

        --- START DECISION LOGIC ---

        **CASE 1: Context is TEXT (RAG Result)**
        You must base your answer STRICTLY on the facts in the text.
        - **Reasoning Rule:** If a fact (e.g., hand injury) has no logical connection to the question (e.g., helmet), state that. DO NOT HALLUCINATE a connection.
        - **RAG Fail Rule:** If the context is "No context found.", respond: "I did not find relevant information in the documents to answer this question."

        **CASE 2: Context is JSON (SQL Result)**
        You must follow this hierarchy of rules:

        **Rule 2.1 (SQL Error):**
        - If the context contains `"Error":` (e.g., `[{"Error": "..."}]`).
        - *Action:* Respond: "I could not formulate a precise answer for this data request because an error occurred."

        **Rule 2.2 (Empty Result):**
        - If the context is an empty list (`[]`).
        - *Action:* Respond that no results were found.
        - *Example:* "No events were found in Abitibi during the last month."

        **Rule 2.3 (Null Result):**
        - If the context is `[{"sum": null}]` or `[{"avg": null}]`.
        - *Action:* Treat `null` as `0`.
        - *Example:* "The total cost is $0."

        **Rule 2.4 (Data Result - The Default Case):**
        - If the context is ANY OTHER JSON (e.g., `[{"sum": 12700}]`, `[{"event_id": 426}, ...]`, `[{"avg": 26332}]`, etc.)
        - *Action:* You MUST treat it as a success. Your only task is to synthesize this data into a clear sentence or bulleted list. DO NOT trigger an error.
        - *Example (Context: `[{"sum": 12700}]`) ->* "The total cost is $12,700."
        - *Example (Context: `[{"event_id": 426}, {"event_id": 590}, ...]`) ->* "I found several incidents involving Alain Mercier, including incidents 426, 590, 615, and others."
        - *Example (Context: `[{"description": "...", "count": 2}]`) ->* "Incident 80 had 2 corrective measures."

        --- END OF LOGIC ---

        **FINAL REMINDER:** Never mention "the context".

        --- CONTEXT ---
        """
        
        # Concaténation sécurisée
        system_prompt = base_prompt + context + "\n--- END CONTEXT ---"
        
        return self._call_bedrock(
            system_prompt=system_prompt, 
            user_content=user_query, 
            temperature=0.1, 
            max_tokens=2048
        )

    def generate_chart_analysis(self, user_query: str, sql_data_json: str, columns: List[str]) -> Dict[str, Any]:
        """
        Analyzes SQL data and the query to suggest a chart.
        """
        
        system_prompt = f"""
        You are an expert data analyst. The user asked a question, and you have the following SQL data in JSON format to answer it.
        Your task is to return a JSON object (and NOTHING ELSE) that analyzes this data for a chart.

        Available columns are: {columns}
        
        --- LOGIC RULES ---
        1.  **If data is `[]` (empty list):**
            - `chart_type` MUST be "list".
            - `title` MUST be an appropriate title (e.g., "No Results").
            - `insight` MUST explain that no data was found (e.g., "No data available for this query.").
        
        2.  **If data is full:**
            - Suggest "bar", "pie", or "line" based on the columns: {columns}.
            - Write a `title` and an `insight`.

        REQUIRED output format (JSON only):
        {{
          "chart_type": "bar" | "pie" | "line" | "list",
          "title": "Chart Title",
          "insight": "A brief analysis of what the data shows."
        }}
        
        --- SQL DATA (JSON) ---
        {sql_data_json}
        --- END SQL DATA ---
        """
        
        response_text = self._call_bedrock(
            system_prompt=system_prompt, 
            user_content=user_query, 
            temperature=0.0, 
            max_tokens=1024
        )
        
        try:
            # Nettoyer la réponse pour extraire le JSON
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                # Fallback
                return {"chart_type": "list", "title": "Raw Data", "insight": "AI analysis failed."}
        except Exception as e:
            print(f"Error parsing JSON for chart analysis: {e}")
            return {"chart_type": "list", "title": "Analysis Error", "insight": str(e)}