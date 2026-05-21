import boto3
 
client = boto3.client(
    "s3vectors",
    region_name="ap-south-1"
)
 
response = client.create_index(
    vectorBucketName="rag-engine-vectorstore",
    dataType="float32",
    indexName="rag-index",
    dimension=1536,          # IMPORTANT
    distanceMetric="cosine"
)
 
print(response)