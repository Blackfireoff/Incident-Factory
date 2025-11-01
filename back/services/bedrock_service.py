import boto3
import os

MODEL_ID = "arn:aws:bedrock:us-east-1:010526273152:inference-profile/us.meta.llama3-2-11b-instruct-v1:0"
REGION = "us-east-1"  # adapte selon ta config AWS

class BedrockChatService:
    def __init__(self):
        self.bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN") 
)
    def analyze_event(self, event_text: str):
        """Analyse un rapport d'évènement avec Llama 3.2"""
        system_prompt = """
        Tu es un assistant expert en analyse de rapports d'incidents et d'évènements industriels.
        Ton rôle est d’identifier les causes, les risques potentiels, et les mesures correctives.
        Fournis des explications claires et structurées.
        """

        messages = [{"role": "user", "content": [{"text": event_text}]}]
        system = [{"text": system_prompt}]
        inference_config = {"temperature": 0.7, "topP": 0.9, "maxTokens": 1500}

        response = self.bedrock.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
        )

        return response["output"]["message"]["content"][0]["text"]
