import boto3
import logging
from botocore.exceptions import ClientError
from pathlib import Path
import configparser
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_aws_credentials():
    try:
        # Read credentials from .aws/credentials
        credentials = configparser.ConfigParser()
        credentials.read('.aws/credentials')
        
        return {
            'aws_access_key_id': credentials['default']['aws_access_key_id'],
            'aws_secret_access_key': credentials['default']['aws_secret_access_key']
        }
    except Exception as e:
        logger.error(f"Error reading credentials: {str(e)}")
        return None

def download_db():
    try:
        # Get credentials
        creds = get_aws_credentials()
        if not creds:
            return False

        # Create S3 client with explicit credentials
        s3_client = boto3.client(
            's3',
            region_name='us-west-1',
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key']
        )

        # Use bucket name directly
        bucket_name = "mgsc410"
        
        logger.info(f"Attempting to download amazon_reviews.db from bucket {bucket_name}...")
        
        # Download the file
        s3_client.download_file(
            bucket_name,
            'amazon_reviews.db',
            'amazon_reviews.db'
        )
        
        logger.info("Successfully downloaded amazon_reviews.db")
        return True

    except ClientError as e:
        logger.error(f"Error downloading file: {str(e)}")
        if e.response['Error']['Code'] == '403':
            logger.error("Access denied. Please check your IAM permissions for this bucket.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    download_db()