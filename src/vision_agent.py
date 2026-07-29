import base64
import json
import boto3
from src.config import get_secret

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=get_secret("AWS_REGION"),
    aws_access_key_id=get_secret("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=get_secret("AWS_SECRET_ACCESS_KEY"),
)

def analyze_screenshot(image_path: str, instruction: str) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": instruction},
                ],
            }
        ],    }

    response = bedrock.invoke_model(
        modelId=get_secret("BEDROCK_MODEL_ID"),
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

if __name__ == "__main__":
    result = analyze_screenshot(
        "screenshot.png",
        "Describe what you see on this page. What are the interactive elements "
        "(buttons, upload areas, inputs) and what would you click first to "
        "test the file upload functionality?"
    )
    print(result)
