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

        # Access point ARN
        access_point_arn = "arn:aws:s3:us-west-1:438537853566:accesspoint/mgsc410-access-point"

        logger.info("Attempting to download amazon_reviews.db...")
        
        # Download the file
        s3_client.download_file(
            access_point_arn,
            'amazon_reviews.db',
            'amazon_reviews.db'
        )
        
        logger.info("Successfully downloaded amazon_reviews.db")
        return True

    except ClientError as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    download_db()