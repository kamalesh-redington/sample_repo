import boto3

client = boto3.client(
    "s3vectors",
    region_name="ap-south-1"
)

# LIST VECTOR BUCKETS
print("\n=== VECTOR BUCKETS ===")

buckets = client.list_vector_buckets()

print(buckets)

# REPLACE WITH YOUR BUCKET
bucket_name = "rag-engine-vectorstore"

print(f"\n=== INDEXES INSIDE {bucket_name} ===")

indexes = client.list_indexes(
    vectorBucketName=bucket_name
)

print(indexes)