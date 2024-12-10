import boto3
import logging
from botocore.exceptions import ClientError
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_db():
    try:
        # Configure the AWS SDK to look for credentials in the local .aws directory
        session = boto3.Session(profile_name='default')
        s3_client = session.client('s3', region_name='us-west-1')

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