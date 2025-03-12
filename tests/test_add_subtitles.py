import unittest
from unittest.mock import patch
import json
import os
import boto3
from moto import mock_aws


import lambda_add_subtitles

class TestSubtitleLambdaHandler(unittest.TestCase):
    @mock_aws
    @patch('lambda_add_subtitles.add_subtitles')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_json_body(self, mock_makedirs, mock_join, mock_add_subtitles):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=bucket_name)

        # Test data
        test_video_key = 'videos/test_video.mp4'
        test_srt_key = 'subtitles/test_video.srt'
        
        # Mock the download_file function to return filenames
        with patch('lambda_add_subtitles.download_file', side_effect=['test_video.mp4', 'test_video.srt']):
            # Mock the add_subtitles function to return the output filename
            mock_add_subtitles.return_value = 'test_video_sub.mp4'
            
            # Mock the upload_file function
            with patch('lambda_add_subtitles.s3.upload_file') as mock_upload:
                mock_upload.return_value = None
                
                # Mock the generate_presigned_url function
                with patch('lambda_add_subtitles.s3.generate_presigned_url') as mock_url:
                    mock_url.return_value = 'https://fake-presigned-url.com/video'
                    
                    # Create a mock event
                    event = {
                        'body': json.dumps({
                            'video': {'key': test_video_key},
                            'srt': {'key': test_srt_key},
                            'bucket': bucket_name
                        })
                    }
                    
                    # Call the lambda_handler
                    response = lambda_add_subtitles.lambda_handler(event, {})
                    
                    # Assert the result
                    self.assertEqual(response['statusCode'], 200)
                    self.assertEqual(response['body']['bucket'], bucket_name)
                    self.assertEqual(response['body']['key'], 'video_sub/test_video_sub.mp4')
                    self.assertEqual(response['body']['url'], 'https://fake-presigned-url.com/video')
                    
                    # Verify the expected calls
                    mock_add_subtitles.assert_called_once_with(
                        'test_video.mp4', 
                        'test_video.srt', 
                        'test_video_sub.mp4'
                    )
                    
                    mock_upload.assert_called_once_with(
                        os.path.join('/tmp', 'test_video_sub.mp4'),
                        bucket_name,
                        'video_sub/test_video_sub.mp4'
                    )
                    
                    mock_url.assert_called_once_with(
                        "get_object",
                        Params={"Bucket": bucket_name, "Key": 'video_sub/test_video_sub.mp4'}
                    )

    @mock_aws
    @patch('lambda_add_subtitles.add_subtitles')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_dict_body(self, mock_makedirs, mock_join, mock_add_subtitles):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=bucket_name)

        # Test data
        test_video_key = 'videos/sample.mp4'
        test_srt_key = 'subtitles/sample.srt'
        
        # Mock the download_file function to return filenames
        with patch('lambda_add_subtitles.download_file', side_effect=['sample.mp4', 'sample.srt']):
            # Mock the add_subtitles function to return the output filename
            mock_add_subtitles.return_value = 'sample_sub.mp4'
            
            # Mock the upload_file function
            with patch('lambda_add_subtitles.s3.upload_file') as mock_upload:
                mock_upload.return_value = None
                
                # Mock the generate_presigned_url function
                with patch('lambda_add_subtitles.s3.generate_presigned_url') as mock_url:
                    mock_url.return_value = 'https://fake-presigned-url.com/video'
                    
                    # Create a mock event with a dict body
                    event = {
                        'body': {
                            'video': {'key': test_video_key},
                            'srt': {'key': test_srt_key},
                            'bucket': bucket_name
                        }
                    }
                    
                    # Call the lambda_handler
                    response = lambda_add_subtitles.lambda_handler(event, {})
                    
                    # Assert the result
                    self.assertEqual(response['statusCode'], 200)
                    self.assertEqual(response['body']['bucket'], bucket_name)
                    self.assertEqual(response['body']['key'], 'video_sub/sample_sub.mp4')
                    
                    # Verify the expected calls
                    mock_add_subtitles.assert_called_once()
                    mock_upload.assert_called_once()
                    mock_url.assert_called_once()

    @mock_aws
    @patch('lambda_add_subtitles.add_subtitles')
    @patch('os.path.join', side_effect=os.path.join)
    @patch('os.makedirs')
    def test_lambda_handler_with_default_bucket(self, mock_makedirs, mock_join, mock_add_subtitles):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        default_bucket = 'cperalesg-video-subtitler'
        s3_client.create_bucket(Bucket=default_bucket)

        # Test data
        test_video_key = 'videos/demo.mp4'
        test_srt_key = 'subtitles/demo.srt'
        
        # Set environment variable for default bucket
        with patch.dict('os.environ', {'bucket_name': default_bucket}):
            # Mock the download_file function
            with patch('lambda_add_subtitles.download_file', side_effect=['demo.mp4', 'demo.srt']):
                # Mock the add_subtitles function
                mock_add_subtitles.return_value = 'demo_sub.mp4'
                
                # Mock the upload_file function
                with patch('lambda_add_subtitles.s3.upload_file') as mock_upload:
                    mock_upload.return_value = None
                    
                    # Mock the generate_presigned_url function
                    with patch('lambda_add_subtitles.s3.generate_presigned_url') as mock_url:
                        mock_url.return_value = 'https://fake-presigned-url.com/video'
                        
                        # Create a mock event without bucket specification
                        event = {
                            'body': json.dumps({
                                'video': {'key': test_video_key},
                                'srt': {'key': test_srt_key}
                            })
                        }
                        
                        # Call the lambda_handler
                        response = lambda_add_subtitles.lambda_handler(event, {})
                        
                        # Assert the result
                        self.assertEqual(response['statusCode'], 200)
                        self.assertEqual(response['body']['bucket'], default_bucket)
                        self.assertEqual(response['body']['url'], 'https://fake-presigned-url.com/video')
                        
                        # Verify expected calls
                        mock_add_subtitles.assert_called_once()
                        mock_upload.assert_called_once()

    def test_download_file(self):
        with mock_aws():
            # Setup S3 bucket and file
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 'test-bucket'
            s3_client.create_bucket(Bucket=bucket_name)
            
            # Create a test file in S3
            s3_client.put_object(
                Bucket=bucket_name,
                Key='videos/test_file.mp4',
                Body=b'test content'
            )
            
            # Mock the download_file function
            with patch('lambda_add_subtitles.s3.download_file') as mock_download:
                mock_download.return_value = None
                
                # Call the function being tested
                result = lambda_add_subtitles.download_file(bucket_name, 'videos/test_file.mp4')
                
                # Assert the result
                self.assertEqual(result, 'test_file.mp4')
                mock_download.assert_called_once_with(
                    bucket_name, 
                    'videos/test_file.mp4', 
                    os.path.join('/tmp', 'test_file.mp4')
                )

    def test_add_subtitles(self):
        video_file = 'test_video.mp4'
        subtitle_file = 'test_subtitle.srt'
        output_file = 'test_video_sub.mp4'
        
        # Mock subprocess.run
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None
            
            # Call the function being tested
            result = lambda_add_subtitles.add_subtitles(video_file, subtitle_file, output_file)
            
            # Assert the result
            self.assertEqual(result, output_file)
            mock_subprocess.assert_called_once()
            
            # Check if the correct ffmpeg command was constructed
            args = mock_subprocess.call_args[0][0]
            self.assertEqual(args[0], 'ffmpeg')
            self.assertEqual(args[1], '-y')
            self.assertEqual(args[2], '-i')
            self.assertEqual(args[3], os.path.join('/tmp', video_file))
            self.assertEqual(args[4], '-vf')
            self.assertTrue(f'subtitles={os.path.join("/tmp", subtitle_file)}' in args[5])
            self.assertEqual(args[6], os.path.join('/tmp', output_file))

if __name__ == '__main__':
    unittest.main()