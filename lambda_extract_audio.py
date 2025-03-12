import json
import subprocess
import boto3
import os
import logging
import shutil


s3 = boto3.client('s3')
AWS_BUCKET_NAME = os.environ.get("bucket_name", "cperalesg-video-subtitler")

tmp_folder = '/tmp/'
shutil.rmtree(tmp_folder, ignore_errors=True)


def lambda_handler(event, context):
    logging.warning("Event: %s", event)
    try:
        body = json.loads(event['body'])
    except:
        body = event['body']
    logging.warning("Body: %s", body)
    
    bucket_name = body.get('bucket', AWS_BUCKET_NAME)
    uid = body.get('uid', '')
    
    video_file = download_video(bucket_name, body['key'])

    audio_file = video_file.split('.')[0] + '.mp3'
    extract_audio(os.path.join(tmp_folder, video_file),
                  os.path.join(tmp_folder, audio_file))
   
    final_key = os.path.join('audio', uid, audio_file)
    s3.upload_file(os.path.join(tmp_folder, audio_file),
                   bucket_name,
                   final_key)

    return {
        'statusCode': 200,
        'body': {'key': final_key,
                 'bucket': bucket_name}
    }


def download_video(bucket, key):
    os.makedirs(tmp_folder, exist_ok=True)
    video_file = key.split('/')[-1]
    s3.download_file(bucket, key, os.path.join(tmp_folder, video_file))
    return video_file


def extract_audio(video_file, audio_file):
    subprocess.run(['ffmpeg', '-i', video_file, '-q:a', '0', '-map', 'a', '-y', audio_file],
                   check=True)
