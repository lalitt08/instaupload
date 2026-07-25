FROM python:3.12-slim

# ffmpeg is needed by moviepy to generate the reel thumbnail on upload.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Let moviepy/imageio use the system ffmpeg instead of downloading one.
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg
# Store the IG session on a mountable volume so it survives restarts.
ENV IG_SESSION_FILE=/data/ig_session.json

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /data holds the persisted IG session; /app/downloads is scratch for reels.
RUN mkdir -p /data /app/downloads
VOLUME ["/data"]

CMD ["python", "bot.py"]
