import unittest
from unittest.mock import patch, MagicMock
import json
import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

# Assuming the module is named 'lambda_get_subtitles'
import lambda_get_subtitles

class TestTranscriptionLambdaHandler(unittest.TestCase):
    @patch('lambda_get_subtitles.boto3.client')
    def test_start_function(self, mock_boto3_client):
        # Setup mock Lambda client
        mock_lambda_client = MagicMock()
        mock_boto3_client.return_value = mock_lambda_client
        
        # Mock event with rawPath set to '/start'
        event = {
            'rawPath': '/start',
            'body': json.dumps({
                'video': {'key': 'videos/test.mp4'},
                'bucket': 'test-bucket',
                'IID': '12345'
            })
        }
        
        # Call the lambda_handler
        response = lambda_get_subtitles.lambda_handler(event, {})
        
        # Assert the result
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(response['body']['message'], 'Processing started...')
        
        # Verify Lambda invocation
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName='transcriptor-lambda',
            InvocationType='Event',
            Payload=json.dumps(event)
        )
    
    @mock_aws
    @patch('lambda_get_subtitles.check_file_exists')
    def test_poll_function_with_srt_exists(self, mock_check_file_exists):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set up mock for check_file_exists
        mock_check_file_exists.return_value = True
        
        # Mock event with poll request
        event = {
            'rawPath': '/poll',
            'body': json.dumps({
                'bucket': bucket_name,
                'IID': '12345'
            })
        }
        
        # Mock generate_presigned_url
        with patch('lambda_get_subtitles.s3.generate_presigned_url') as mock_url:
            mock_url.side_effect = [
                'https://test-bucket.s3.amazonaws.com/processed/srt/12345.srt',
                'https://test-bucket.s3.amazonaws.com/processed/txt/12345.txt'
            ]
            
            # Call the lambda_handler
            response = lambda_get_subtitles.lambda_handler(event, {})
            
            # Assert the result
            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(response['body']['subtitles']['key'], 'processed/srt/12345.srt')
            self.assertEqual(response['body']['subtitles']['bucket'], bucket_name)
            self.assertEqual(response['body']['subtitles']['url'], 
                            'https://test-bucket.s3.amazonaws.com/processed/srt/12345.srt')
            self.assertEqual(response['body']['text']['key'], 'processed/txt/12345.txt')
            self.assertEqual(response['body']['text']['bucket'], bucket_name)
            self.assertEqual(response['body']['text']['url'], 
                            'https://test-bucket.s3.amazonaws.com/processed/txt/12345.txt')
            
            # Verify check_file_exists call
            mock_check_file_exists.assert_called_once_with(
                bucket_name=bucket_name,
                file_key='processed/srt/12345.srt'
            )
            
            # Verify generate_presigned_url calls
            self.assertEqual(mock_url.call_count, 2)
    
    @mock_aws
    @patch('lambda_get_subtitles.check_file_exists')
    def test_poll_function_with_error_file(self, mock_check_file_exists):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set up mock for check_file_exists to first return False (SRT doesn't exist)
        # then True (error file exists)
        mock_check_file_exists.side_effect = [False, True]
        
        # Mock event with poll request
        event = {
            'rawPath': '/poll',
            'body': json.dumps({
                'bucket': bucket_name,
                'IID': '12345'
            })
        }
        
        # Call the lambda_handler
        response = lambda_get_subtitles.lambda_handler(event, {})
        
        # Assert the result
        self.assertEqual(response['statusCode'], 500)
        self.assertEqual(response['body']['message'], 'Error in the Transcriptor')
        
        # Verify check_file_exists calls
        mock_check_file_exists.assert_any_call(
            bucket_name=bucket_name,
            file_key='processed/srt/12345.srt'
        )
        mock_check_file_exists.assert_any_call(
            bucket_name=bucket_name,
            file_key='processed/error/12345.error'
        )
    
    @mock_aws
    @patch('lambda_get_subtitles.check_file_exists')
    def test_poll_function_still_waiting(self, mock_check_file_exists):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set up mock for check_file_exists to return False for both checks
        mock_check_file_exists.return_value = False
        
        # Mock event with poll request
        event = {
            'rawPath': '/poll',
            'body': json.dumps({
                'bucket': bucket_name,
                'IID': '12345'
            })
        }
        
        # Call the lambda_handler
        response = lambda_get_subtitles.lambda_handler(event, {})
        
        # Assert the result
        self.assertEqual(response['statusCode'], 202)
        self.assertEqual(response['body']['message'], 'Still waiting...')
        
        # Verify check_file_exists was called twice (once for SRT, once for error)
        self.assertEqual(mock_check_file_exists.call_count, 2)
    
    @mock_aws
    def test_check_file_exists_when_file_exists(self):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        file_key = 'test/file.txt'
        
        # Create the bucket and put an object
        s3_client.create_bucket(Bucket=bucket_name)
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=b'test content')
        
        # Test the function
        result = lambda_get_subtitles.check_file_exists(bucket_name, file_key)
        
        # Assert the result
        self.assertTrue(result)
    
    @mock_aws
    def test_check_file_exists_when_file_does_not_exist(self):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        file_key = 'test/nonexistent.txt'
        
        # Create the bucket but don't put any object
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Need to patch head_object to raise the proper ClientError
        with patch('lambda_get_subtitles.s3.head_object') as mock_head_object:
            # Create a ClientError with 404 code
            error_response = {'Error': {'Code': '404'}}
            mock_head_object.side_effect = ClientError(error_response, 'HeadObject')
            
            # Test the function
            result = lambda_get_subtitles.check_file_exists(bucket_name, file_key)
            
            # Assert the result
            self.assertFalse(result)
    
    @mock_aws
    def test_check_file_exists_with_other_error(self):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        file_key = 'test/file.txt'
        
        # Create the bucket
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Need to patch head_object to raise a different ClientError
        with patch('lambda_get_subtitles.s3.head_object') as mock_head_object:
            # Create a ClientError with 403 code
            error_response = {'Error': {'Code': '403'}}
            mock_head_object.side_effect = ClientError(error_response, 'HeadObject')
            
            # Test the function - should raise the exception
            with self.assertRaises(ClientError):
                lambda_get_subtitles.check_file_exists(bucket_name, file_key)
    
    @mock_aws
    @patch('lambda_get_subtitles.check_file_exists')
    def test_poll_function_with_dict_body(self, mock_check_file_exists):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Set up mock for check_file_exists
        mock_check_file_exists.return_value = True
        
        # Mock event with poll request and dict body
        event = {
            'rawPath': '/poll',
            'body': {
                'bucket': bucket_name,
                'IID': '12345'
            }
        }
        
        # Mock generate_presigned_url
        with patch('lambda_get_subtitles.s3.generate_presigned_url') as mock_url:
            mock_url.side_effect = [
                'https://test-bucket.s3.amazonaws.com/processed/srt/12345.srt',
                'https://test-bucket.s3.amazonaws.com/processed/txt/12345.txt'
            ]
            
            # Call the lambda_handler
            response = lambda_get_subtitles.lambda_handler(event, {})
            
            # Assert the result
            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(response['body']['subtitles']['key'], 'processed/srt/12345.srt')
            
            # Verify check_file_exists call
            mock_check_file_exists.assert_called_once()

if __name__ == '__main__':
    unittest.main()