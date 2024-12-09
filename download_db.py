import boto3
import os
from botocore.exceptions import ClientError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_db_from_s3(bucket_name, s3_key, local_file='amazon_reviews.db'):
    """
    Download the database file from S3
    
    Args:
        bucket_name (str): Name of the S3 bucket
        s3_key (str): Path to the file in S3 bucket
        local_file (str): Local path where the file should be saved
    """
    # Create an S3 client
    s3_client = boto3.client('s3')
    
    try:
        # Check if file already exists locally
        if os.path.exists(local_file):
            logger.info(f"Database file already exists at {local_file}")
            return
        
        logger.info(f"Downloading database from s3://{bucket_name}/{s3_key}")
        s3_client.download_file(bucket_name, s3_key, local_file)
        logger.info(f"Successfully downloaded database to {local_file}")
        
    except ClientError as e:
        logger.error(f"Error downloading database: {str(e)}")
        raise

if __name__ == "__main__":
    # Replace these with your actual S3 bucket and key
    BUCKET_NAME = "mgsc410"
    S3_KEY = "amazon_reviews.db"  # Update this if your file is in a different path in S3
    
    download_db_from_s3(BUCKET_NAME, S3_KEY)
