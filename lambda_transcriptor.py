import time
import os
import logging
import whisper
from whisper.model import ModelDimensions, Whisper
import boto3
import io
import pickle
import torch
import gc
import psutil
import json
import shutil


MODEL_NAME = os.environ.get('model', 'medium.pt')
logging.warning('Model %s selected', MODEL_NAME)


# AWS S3 Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "cperalesg-video-subtitler")
s3_client = boto3.client("s3", region_name=AWS_REGION)


def memory_usage():
    return psutil.Process().memory_info().rss / (1024 * 1024)  # Convert bytes to MB


def load_model_bytes(checkpoint_file):
    with io.BytesIO(checkpoint_file) as fp:
        checkpoint = torch.load(fp, map_location='cpu')
    
    dims = ModelDimensions(**checkpoint["dims"])
    model = Whisper(dims)
    model.load_state_dict(checkpoint["model_state_dict"])

    return model


def load_model_pickle(pickle_file):
    return pickle.load(pickle_file)


def get_session(context='aws'):
    if context == 'local':
        session = boto3.Session(region_name='us-east-1')
    else:
        session = boto3.Session()
    return session


def load_model_from_s3(s3_bucket='cperalesg-whisper-model',
                       file_prefix='',
                       model_name=MODEL_NAME,
                       context='aws'):
    session = get_session(context)
    s3 = session.client('s3')
    file_name = os.path.join(file_prefix, model_name)
    obj = s3.get_object(Bucket=s3_bucket, Key=file_name)

    logging.warning('Loading model %s', model_name)
    
    if model_name[-3:] == '.pt':
        return load_model_bytes(obj['Body'].read())
    else:
        return load_model_pickle(obj['Body'])


def get_model():
    try:
        return load_model_from_s3(model_name=MODEL_NAME)
    except Exception as e:
        logging.error("Model %s not loaded from S3, %s",
                    MODEL_NAME, str(e))
        raise e


MODEL = get_model()
logging.warning("Model loaded!")


def lambda_handler(event, context):
    try:
        message = json.loads(event['body'])
    except:
        message = event['body']
    logging.warning("Body: %s", message)

    if message.get('warmup', False):
        logging.warning("Warm up!")
        return {"statusCode": 200,
                "body": {"message": "Warming up the transcriptor"}}

    output_folder = '/tmp/'
    shutil.rmtree(output_folder, ignore_errors=True)
    os.makedirs(output_folder, exist_ok=True)

    try:
        iid = message['IID']
    except KeyError:
        return {"statusCode": 400,
                "error": "\'IID\' key should be included in the body"}

    # Save the audio file
    audio_file = os.path.join(output_folder,
                                "received_audio.mp3")
    try:
        s3_client.download_file(AWS_BUCKET_NAME,
                                message['audio'],
                                audio_file)
    except KeyError:
        return {"error": '\'audio\' key should be in JSON body',
                "statusCode": 400}
    except Exception as e:
            return {"error": str(e),
                    "statusCode": 500}

    # Transcript audio
    logging.warning(f"Processing audio {message['audio']} with ID {iid}...")
    start = time.perf_counter()
    transcription = get_transcription(audio_file, MODEL)
    duration = time.perf_counter() - start
    logging.warning("Transcription finished! Process lasts %.2f seconds", duration)
    gc.collect()
    logging.info('Memory usage after transcription and gc: %.2f', memory_usage())

    text_file = os.path.join(output_folder, f"{iid}.txt") 
    text_file = save_text(transcription['text'], text_file)
    # Upload back to S3
    s3_output_key_txt = f"processed/text/{iid}.txt"
    s3_client.upload_file(text_file, AWS_BUCKET_NAME, s3_output_key_txt)

    srt_file = os.path.join(output_folder, f"{iid}.srt")
    srt_file = save_transcription(transcription['segments'], srt_file)

    # Upload back to S3
    s3_output_key_srt = f"processed/srt/{iid}.srt"
    s3_client.upload_file(srt_file, AWS_BUCKET_NAME, s3_output_key_srt)
    logging.warning('SRT file uploaded to %s', s3_output_key_srt)



def save_transcription(data, srt_file):
    with open(srt_file, "w") as f:
        for idx, entry in enumerate(data, start=1):
            f.write(f"{idx}\n")
            start = float(entry['start'])
            start_formatted = seconds_to_hh_mm_seconds(start)
            end = float(entry['end'])
            end_formatted = seconds_to_hh_mm_seconds(end)
            f.write(f"{start_formatted} --> {end_formatted}\n")
            f.write(f"{entry['text']}\n\n")

    return srt_file


def save_text(data, text_file):
    with open(text_file, "w") as f:
        f.write(data)
    
    return text_file


def seconds_to_hh_mm_seconds(total_seconds):
    # Convert seconds to hours, minutes, and seconds
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    miliseconds = (seconds - int(seconds)) * 1000
    # Return the formatted time as HH:MM:seconds
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(miliseconds)}"


def get_transcription(audio, MODEL):
    logging.warning('Transcribiendo...')
    logging.warning('Número de threads: %s',
                    whisper.torch.get_num_threads())
    logging.info('Memory usage before gc and transcription: %.2f', memory_usage())
    gc.collect()
    logging.info('Memory usage after gc and before transcription: %.2f', memory_usage())
    transcription = MODEL.transcribe(audio,
                    # language='es',
                    temperature=0.0,
                    fp16=False,
                    word_timestamps=False)
    logging.info('Memory usage after transcription: %.2f', memory_usage())
    
    segments = transcription['segments']
    text = remove_beginning_whitespace(transcription['text'])

    new_segments = [{'start': s['start'],
                     'end': s['end'],
                     'text': remove_beginning_whitespace(s['text'])}
                    for s in segments]
    
    del transcription
    
    return {'segments': new_segments,
            'text': text}


def remove_beginning_whitespace(text):
    # Remove space at the beggining
    space = True
    while space:
        if text[0] == ' ':
            text = text[1:]
        else:
            space = False
    return text
