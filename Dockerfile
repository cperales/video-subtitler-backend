FROM public.ecr.aws/lambda/python:3.12

# Install dependencies for downloading/extracting
RUN dnf install -y xz tar gzip && dnf clean all

# Download and install ffmpeg static build
RUN curl -LO https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    cp ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-*-amd64-static ffmpeg-release-amd64-static.tar.xz

# Install dependencies
RUN pip install -U --no-cache-dir pip && pip install --no-cache-dir \
    openai-whisper==20240930 \
    psutil \
    boto3 \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy transcriptor code
COPY lambda_transcriptor.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_transcriptor.lambda_handler" ]