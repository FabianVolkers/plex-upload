# Plex Uploader
A simple Flask app for uploading media files to a plex server with built-in parsing and renaming of TV Show episodes powered by [tvnamer](https://github.com/dbr/tvnamer).

## Deploy
The easiest way to deploy is using docker. Either pull the image directly for the Docker Hub or clone the repository and build it yourself.
```zsh
# Pull the image
docker pull fabiserv/plex-upload

# Download the compose file
curl "https://github.com/FabianVolkers/plex-upload/blob/main/docker-compose.yml" -o docker-compose.yml

# Start the container using docker-compose
docker-compose up
```

## Configuration
There are several configuration options, most with sensible defaults.

## Development
After cloning the repo
```zsh
cd plex-upload

# Copy example config.py, don't forget to add your config values
mkdir instance
cp config.example.py instance/config.py

# Setup virtual environment and install requirements
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup flask env vars and run
export FLASK_APP=plex-upload
export FLASK_ENV=development
flask run
```