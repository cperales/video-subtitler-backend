import unittest
from unittest.mock import patch
import json
import os
import boto3
from moto import mock_aws


import lambda_extract_audio

class TestLambdaHandler(unittest.TestCase):
    @mock_aws
    @patch('lambda_extract_audio.extract_audio')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_json_body(self, mock_makedirs, mock_join, mock_extract_audio):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create test data
        test_video_key = 'videos/test_video.mp4'
        test_uid = 'test123'
        
        # Mock the download_file function
        with patch('lambda_extract_audio.s3.download_file') as mock_download:
            mock_download.return_value = None
            
            # Mock the upload_file function
            with patch('lambda_extract_audio.s3.upload_file') as mock_upload:
                mock_upload.return_value = None
                
                # Create a mock event
                event = {
                    'body': json.dumps({
                        'key': test_video_key,
                        'bucket': bucket_name,
                        'uid': test_uid
                    })
                }
                
                # Call the lambda_handler
                response = lambda_extract_audio.lambda_handler(event, {})
                
                # Assert the result
                self.assertEqual(response['statusCode'], 200)
                self.assertEqual(response['body']['bucket'], bucket_name)
                self.assertEqual(response['body']['key'], f'audio/{test_uid}/test_video.mp3')
                
                # Verify the expected calls
                mock_download.assert_called_once_with(
                    bucket_name, 
                    test_video_key, 
                    os.path.join('/tmp/', 'test_video.mp4')
                )
                
                mock_extract_audio.assert_called_once_with(
                    os.path.join('/tmp/', 'test_video.mp4'),
                    os.path.join('/tmp/', 'test_video.mp3')
                )
                
                mock_upload.assert_called_once_with(
                    os.path.join('/tmp/', 'test_video.mp3'),
                    bucket_name,
                    f'audio/{test_uid}/test_video.mp3'
                )

    @mock_aws
    @patch('lambda_extract_audio.extract_audio')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_dict_body(self, mock_makedirs, mock_join, mock_extract_audio):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create test data
        test_video_key = 'videos/test_video.mp4'
        
        # Mock the download_file function
        with patch('lambda_extract_audio.s3.download_file') as mock_download:
            mock_download.return_value = None
            
            # Mock the upload_file function
            with patch('lambda_extract_audio.s3.upload_file') as mock_upload:
                mock_upload.return_value = None
                
                # Create a mock event with a dict body instead of JSON string
                event = {
                    'body': {
                        'key': test_video_key,
                        'bucket': bucket_name
                    }
                }
                
                # Call the lambda_handler
                response = lambda_extract_audio.lambda_handler(event, {})
                
                # Assert the result
                self.assertEqual(response['statusCode'], 200)
                self.assertEqual(response['body']['bucket'], bucket_name)
                self.assertEqual(response['body']['key'], 'audio/test_video.mp3')
                
                # Verify the expected calls
                mock_download.assert_called_once()
                mock_extract_audio.assert_called_once()
                mock_upload.assert_called_once()

    @mock_aws
    @patch('lambda_extract_audio.extract_audio')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_default_bucket(self, mock_makedirs, mock_join, mock_extract_audio):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        default_bucket = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=default_bucket)

        # Create test data
        test_video_key = 'videos/test_video.mp4'
        
        # Mock the download_file function
        with patch('lambda_extract_audio.s3.download_file') as mock_download:
            mock_download.return_value = None
            
            # Mock the upload_file function
            with patch('lambda_extract_audio.s3.upload_file') as mock_upload:
                mock_upload.return_value = None
                
                # Create a mock event without specifying bucket
                event = {
                    'body': json.dumps({
                        'key': test_video_key
                    })
                }
                
                # Call the lambda_handler
                response = lambda_extract_audio.lambda_handler(event, {})
                
                # Assert the result
                self.assertEqual(response['statusCode'], 200)
                self.assertEqual(response['body']['bucket'], default_bucket)
                self.assertEqual(response['body']['key'], 'audio/test_video.mp3')
                
                # Verify the expected calls
                mock_download.assert_called_once_with(
                    default_bucket, 
                    test_video_key, 
                    os.path.join('/tmp/', 'test_video.mp4')
                )

if __name__ == '__main__':
    unittest.main()