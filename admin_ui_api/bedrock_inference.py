import json
import os
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BEDROCK_MODEL_ID = "amazon.nova-pro-v1:0"
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

import boto3
import json

client = boto3.client("bedrock-runtime",region_name="ap-south-1")

response = client.converse(
    modelId="amazon.nova-pro-v1:0",
    messages=[
        {
            "role": "user",
            "content": [{"text": "Hello"}]
        }
    ]
)

print(response["output"]["message"]["content"][0]["text"])

