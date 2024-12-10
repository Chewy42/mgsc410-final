import boto3

# Create an S3 client
s3_client = boto3.client('s3')

# Access point ARN format
access_point_arn = f"arn:aws:s3:us-west-1:438537853566:accesspoint/mgsc410-access-point"

# To download the file
s3_client.download_file(
    access_point_arn,  # Use access point ARN instead of bucket name
    'amazon_reviews.db',  # Source file name in S3
    'amazon_reviews.db'   # Local destination file name
)