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
            print("Erreur: Impossible d'initialiser le client Boto3 Bedrock.")
            raise Exception(f"Erreur client Bedrock: {e}")

    def _call_bedrock(self, system_prompt: str, user_content: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
        """Fonction helper pour appeler l'API Bedrock converse."""
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
            print(f"Erreur lors de l'appel à Bedrock (converse): {e}")
            if "AccessDeniedException" in str(e):
                print(f"Erreur: Accès refusé. Avez-vous demandé l'accès au modèle '{MODEL_ID}' dans la console Bedrock ?")
            raise e 

    def decide_tool(self, user_query: str) -> Literal["sql", "search"]:
        """
        Décide quel outil utiliser (SQL ou RAG/Recherche sémantique).
        """
        system_prompt = f"""
        Tu es un agent de routage intelligent. Ton but est de décider quel outil utiliser pour répondre à la question de l'utilisateur.
        Tu as deux choix :
        1.  "sql": Utilise cet outil pour les questions nécessitant de compter, lister, agréger, ou filtrer des données structurées (ex: "Combien...", "Liste tous les incidents à...", "Donne-moi le top 5...", "Génère un graphique...").
        2.  "search": Utilise cet outil pour les questions ouvertes, sémantiques, ou de raisonnement (ex: "Pourquoi...", "Comment prévenir...", "Que s'est-il passé...", "Quels incidents impliquent des escaliers...").

        Exemples de routage :
        -   Question: "Affiche tous les événements du dernier mois en Abitibi" -> "sql"
        -   Question: "Quels événements impliquent des escaliers par temps froid?" -> "search"
        -   Question: "Liste toutes les blessures qui auraient pu être évitées avec un casque" -> "search"
        -   Question: "Quels types de machines sont impliquées dans le plus de blessures ?" -> "sql"
        -   Question: "Propose un plan d'action pour réduire la gravité..." -> "search"

        Réponds UNIQUEMENT par "sql" ou "search". Ne dis rien d'autre.
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

    def generate_sql_query(self, schema: str, user_query: str) -> str:
        """
        Génère une requête SQL à partir de la question de l'utilisateur et du schéma.
        """
        system_prompt = f"""
        Tu es un expert en PostgreSQL. Étant donné le schéma de base de données ci-dessous, écris une seule requête SELECT, efficace et lisible, pour répondre à la question de l'utilisateur.
        -   Ne retourne QUE la requête SQL, sans aucune explication, commentaire ou balise (comme ```sql).
        
        --- RÈGLES STRICTES ---
        1.  **Obéissance aux indices :** Les 'Indices de valeurs' (ex: 'INJURY') SONT la seule source de vérité. TU DOIS les utiliser.
        
        2.  **Utilisation des IDs :** Si la question de l'utilisateur mentionne un ID spécifique (ex: "incident 83"), tu DOIS utiliser cet ID. N'AJOUTE PAS d'autres filtres textuels (comme `description = '...'`). L'ID est suffisant et prioritaire.
            -   *Exemple de question :* "Coût des mesures pour l'incident 83 (le déversement)"
            -   *Bon SQL :* `... WHERE e.event_id = 83`
            -   *Mauvais SQL :* `... WHERE e.event_id = 83 AND e.description = 'le déversement'`
        
        3.  **Respect des jointures :** Tu NE DOIS PAS inventer de colonnes. Pour lier `event` et `corrective_measure`, tu DOIS utiliser `event_corrective_measure`.
        
        4.  **Contexte des COUNT :** Si la question demande un simple 'COUNT', préserve le contexte (ex: `SELECT type, COUNT(*) ... GROUP BY type`).
        --- FIN DES RÈGLES ---

        --- SCHÉMA ---
        {schema}
        --- FIN SCHÉMA ---
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
        Génère une réponse en langage naturel basée sur un contexte (RAG ou SQL).
        """
        
        base_prompt = """
        Tu es un assistant IA expert en analyse d'incidents de sécurité et d'environnement.
        Ton objectif est de répondre à la question de l'utilisateur en te basant sur les faits du contexte fourni.
        Tu ne dois **JAMAIS** mentionner que tu te bases sur un "contexte" ou "les informations fournies". Réponds directement.

        --- DÉBUT DE LA LOGIQUE DE DÉCISION ---

        **CAS 1 : Le contexte est du TEXTE (Résultat de recherche RAG)**
        Tu dois te baser STRICTEMENT sur les faits du texte.
        - **Règle de Raisonnement :** Si un fait (ex: blessure à la main) n'a aucun lien logique avec la question (ex: casque), dis-le. NE PAS HALLUCINER de lien (ex: "le casque aurait protégé son visage").
        - **Règle d'échec RAG :** Si le texte ne contient aucune information pertinente (Test 7), réponds : "Je n'ai pas trouvé d'informations pertinentes dans les documents pour répondre à cette question."

        **CAS 2 : Le contexte est du JSON (Résultat de SQL)**
        Tu dois suivre cette hiérarchie de règles :

        **Règle 2.1 (Erreur SQL) :**
        - Si le contexte contient `"Erreur":` (ex: `[{"Erreur": "..."}]`).
        - *Action :* Réponds : "Je n'ai pas pu formuler de réponse précise pour cette demande de données car une erreur est survenue."

        **Règle 2.2 (Résultat Vide) :**
        - Si le contexte est une liste vide (`[]`).
        - *Action :* Réponds qu'aucun résultat n'a été trouvé.
        - *Exemple :* "Aucun événement n'a été trouvé en Abitibi durant le dernier mois."

        **Règle 2.3 (Résultat Null) :**
        - Si le contexte est `[{"sum": null}]` ou `[{"avg": null}]`.
        - *Action :* Traite `null` comme `0`.
        - *Exemple :* "Le coût total est de 0 $."

        **Règle 2.4 (Résultat de Données - Le Cas Général) :**
        - Si le contexte est N'IMPORTE QUEL AUTRE JSON (ex: `[{"sum": 12700}]`, `[{"event_id": 426}, ...]`, `[{"avg": 26332}]`, etc.)
        - *Action :* Tu DOIS le considérer comme une réussite. Ta seule tâche est de synthétiser ces données en une phrase ou une liste claire. NE PAS DÉCLENCHER D'ERREUR.
        - *Exemple (Contexte: `[{"sum": 12700}]`) ->* "Le coût total est de 12 700 $."
        - *Exemple (Contexte: `[{"event_id": 426}, {"event_id": 590}, ...]`) ->* "J'ai trouvé plusieurs incidents impliquant Alain Mercier, notamment les incidents 426, 590, 615, et d'autres."
        - *Exemple (Contexte: `[{"description": "...", "count": 2}]`) ->* "L'incident 80 a eu 2 mesures correctives."

        --- FIN DE LA LOGIQUE ---

        **RAPPEL FINAL :** Ne parle jamais du "contexte".

        --- CONTEXTE ---
        """
        
        # Concaténation sécurisée
        system_prompt = base_prompt + context + "\n--- FIN DU CONTEXTE ---"
        
        return self._call_bedrock(
            system_prompt=system_prompt, 
            user_content=user_query, 
            temperature=0.1, 
            max_tokens=2048
        )

    def generate_chart_analysis(self, user_query: str, sql_data_json: str) -> Dict[str, Any]:
        """
        Analyse les données SQL et la requête pour suggérer un graphique.
        Retourne une analyse JSON.
        """
        system_prompt = f"""
        Tu es un analyste de données expert. L'utilisateur t'a posé une question et tu as les données SQL suivantes en format JSON pour y répondre.
        Ta tâche est de renvoyer un objet JSON (et RIEN D'AUTRE) qui analyse ces données.

        1.  Analyse la question de l'utilisateur et les données.
        2.  Suggère le type de graphique le plus pertinent (choisis parmi: "bar", "pie", "line", "list").
            - "bar" pour les comparaisons (ex: top 5).
            - "pie" pour les proportions (ex: par type).
            - "line" pour les tendances temporelles.
            - "list" si les données ne sont pas graphiques (ex: une liste d'événements).
        3.  Crée un titre (title) concis pour le graphique.
        4.  Rédige une courte analyse (insight) des données.

        Format de sortie OBLIGATOIRE (JSON uniquement) :
        {{
          "chart_type": "bar" | "pie" | "line" | "list",
          "title": "Titre du graphique",
          "insight": "Une brève analyse de ce que les données montrent."
        }}

        --- DONNÉES SQL (JSON) ---
        {sql_data_json}
        --- FIN DES DONNÉES ---
        """
        
        # Le contenu utilisateur est la requête originale pour donner du contexte
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
                return {"chart_type": "list", "title": "Données Brutes", "insight": "L'analyse IA a échoué, voici les données."}
        except Exception as e:
            print(f"Erreur de parsing JSON pour l'analyse de graphique: {e}")
            return {"chart_type": "list", "title": "Erreur d'Analyse", "insight": str(e)}