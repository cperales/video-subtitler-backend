import json
import subprocess
import boto3
import os
import logging


s3 = boto3.client('s3')
AWS_BUCKET_NAME = os.environ.get("bucket_name", "cperalesg-video-subtitler")
tmp_folder = '/tmp'


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
    except:
        body = event['body']

    bucket_name = body.get('bucket', AWS_BUCKET_NAME)
    os.makedirs(tmp_folder, exist_ok=True)

    video_file = download_file(bucket_name, body['video']['key'])
    srt_file = download_file(bucket_name, body['srt']['key'])

    filename, file_extension = os.path.splitext(video_file)
    output_file = filename + '_sub' + file_extension
    output_file = add_subtitles(video_file, srt_file, output_file)
   
    final_key = os.path.join('video_sub', output_file)
    logging.warning("Uploading %s to %s", os.path.join(tmp_folder, output_file),
                    final_key)
    response = s3.upload_file(os.path.join(tmp_folder, output_file),
                              bucket_name,
                              final_key)

    params = {
            "Bucket": bucket_name,
            "Key": final_key,
        }
    url_video_sub = s3.generate_presigned_url("get_object",
                                              Params=params)

    return {
        'statusCode': 200,
        'body': {'key': final_key,
                 'bucket': bucket_name,
                 'url': url_video_sub}
    }


def download_file(bucket, key):
    filename = key.split('/')[-1]
    logging.warning("Downloading %s", os.path.join(tmp_folder, filename))
    s3.download_file(bucket, key, os.path.join(tmp_folder, filename))
    return filename


def add_subtitles(video_file, subtitle_file, output_file):
    command = [
        "ffmpeg",
        "-y",                                                           # Overwrite if the file exists 
        "-i", os.path.join(tmp_folder, video_file),                     # Input video
        "-vf", f"subtitles={os.path.join(tmp_folder, subtitle_file)}",  # Add subtitles filter
        os.path.join(tmp_folder, output_file)                           # Output video with subtitles
    ]
    logging.warning("Running %s", ' '.join(command))
    subprocess.run(command, check=True)
    return output_file
