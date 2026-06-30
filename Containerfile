# Container image for the riff web frontend (`riff serve`).
#
# Build from the repo root:   podman build -t riff-web .
# Run:                        podman run -p 8080:8080 -v ~/Music:/music:z \
#                                 -e RIFF_MUSIC_DIR=/music riff-web
FROM python:3.12-slim

# ffmpeg is required by yt-dlp for audio extraction / format conversion.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir '.[web]'

ENV RIFF_MUSIC_DIR=/music
EXPOSE 8080

# Bind to all interfaces inside the container; the host/compose layer decides
# which networks the published port is exposed on.
CMD ["riff", "serve", "--host", "0.0.0.0", "--port", "8080"]
