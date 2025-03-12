# Video Subtitler backend


This is the backend for website [subtitulatuvideo.es](https://subtitulatuvideo.es/), a project by @cperales and @jomaroru7, aims to provide a website to get your videos subtitled using Whisper as the core of the subtitler IA.

## Test locally

Tests with mocks have been included, except for the main function. You can test the rest of the functions by running:

```python
python -m unittest tests/test_add_subtitles.py
python -m unittest tests/test_get_subtitles.py
python -m unittest tests/test_extract_audio.py
```
