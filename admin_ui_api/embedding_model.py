import boto3
import json
import numpy as np
from numpy.linalg import norm

# ==========================================
# AWS CONFIG
# ==========================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL_ID = "amazon.titan-embed-text-v2:0"

# ==========================================
# CREATE BEDROCK CLIENT
# ==========================================

bedrock = boto3.client(
    service_name="bedrock-runtime"
)

# ==========================================
# FUNCTION TO GENERATE EMBEDDING
# ==========================================

def get_embedding(text):

    body = {
        "inputText": text
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )

    response_body = json.loads(response["body"].read())

    embedding = response_body["embedding"]

    return embedding

# ==========================================
# TEST TEXTS
# ==========================================

text1 = "Artificial intelligence is transforming healthcare."
text2 = "AI is revolutionizing medical diagnostics."
text3 = "The cricket match was exciting."

# ==========================================
# GENERATE EMBEDDINGS
# ==========================================

emb1 = get_embedding(text1)
emb2 = get_embedding(text2)
emb3 = get_embedding(text3)

print("Embedding Dimension:", len(emb1))

# ==========================================
# COSINE SIMILARITY
# ==========================================

def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)

    return np.dot(v1, v2) / (norm(v1) * norm(v2))

sim_12 = cosine_similarity(emb1, emb2)
sim_13 = cosine_similarity(emb1, emb3)

print("\nSimilarity Results")
print("-" * 50)

print(f"Text1 vs Text2: {sim_12:.4f}")
print(f"Text1 vs Text3: {sim_13:.4f}")

# ==========================================
# INTERPRETATION
# ==========================================

print("\nInterpretation:")

if sim_12 > sim_13:
    print("Embedding model is working correctly.")
else:
    print("Unexpected similarity results.")