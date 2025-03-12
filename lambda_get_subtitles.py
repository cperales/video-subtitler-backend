import json
import subprocess
import boto3
import os
from botocore.exceptions import ClientError
import logging


s3 = boto3.client('s3')
AWS_BUCKET_NAME = os.environ.get("bucket_name", "cperalesg-video-subtitler")
tmp_folder = '/tmp/'


def check_file_exists(bucket_name: str, file_key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            # Object does not exist
            return False
        else:
            # Other error (e.g., permission denied)
            raise e


def start(event):
    client = boto3.client('lambda')
    client.invoke(
        FunctionName='transcriptor-lambda',
        InvocationType='Event',  # Asynchronous invocation
        Payload=json.dumps(event)
    )
    return {
        'statusCode': 200,
        'body': {'message': 'Processing started...'}
    }


def poll(event):
    try:
        body = json.loads(event['body'])
    except:
        body = event['body']

    bucket_name = body.get('bucket', AWS_BUCKET_NAME)
    iid = body['IID']
    s3_output_key_srt = f"processed/srt/{iid}.srt"
    check = check_file_exists(bucket_name=bucket_name,
                              file_key=s3_output_key_srt)
    if check:
        logging.warning("SRT with IID %s file exists", iid)
        params = {
            "Bucket": bucket_name,
            "Key": s3_output_key_srt,
        }
        url_srt = s3.generate_presigned_url("get_object",
                                            Params=params)
        # Text is also finished
        s3_output_key_txt = f"processed/txt/{iid}.txt"
        params = {
            "Bucket": bucket_name,
            "Key": s3_output_key_txt,
        }
        url_txt = s3.generate_presigned_url("get_object",
                                            Params=params)
        return {
        'statusCode': 200,
        'body': {"text": {"key": s3_output_key_txt,
                          "bucket": bucket_name,
                          "url": url_txt},
                 "subtitles": {"key": s3_output_key_srt,
                               "bucket": bucket_name,
                               "url": url_srt}
        }}
    else:
        s3_output_key_error = f"processed/error/{iid}.error"
        error_check = check_file_exists(bucket_name=bucket_name,
                                        file_key=s3_output_key_error)
        if error_check:
            logging.warning("IID %s results in an error", iid)
            return {
            "statusCode": 500,
            'body': {"message": "Error in the Transcriptor"}
        }
        else:
            logging.warning("Still waiting for IID %s", iid)
            return {
                "statusCode": 202,
                'body': {"message": "Still waiting..."}
            }


def lambda_handler(event, context):
    path = event.get('rawPath', '')
    logging.warning("Event: %s", event)
    
    if path == '/start':
        return start(event)
    else:
        return poll(event)
