# GUI YouTube Downloader

A simple Windows desktop app for downloading YouTube videos, built with Python and Tkinter on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Paste a link and click **Download**
- Progress bar and live log
- Choose the save folder (defaults to your Downloads folder)
- Three formats:
  - **Best quality (MP4)**: best video plus best audio, merged into one MP4
  - **Plays everywhere (H.264 MP4)**: works in almost any player
  - **Audio only (M4A)**
- Cancel a download partway through
- Downloads a single video even if the link is inside a playlist

## Requirements

- Windows with [Python 3](https://www.python.org/downloads/) (Tkinter is included)
- yt-dlp:
  ```
  pip install --user -U yt-dlp
  ```
- ffmpeg (needed to merge video and audio):
  ```
  winget install --id Gyan.FFmpeg -e
  ```

The app finds yt-dlp and ffmpeg on your PATH, or in their default pip and winget install locations.

## Usage

Double-click `YouTube Downloader.pyw`, or run:

```
pythonw "YouTube Downloader.pyw"
```

## Note

Download only videos you have the right to download, and follow YouTube's Terms of Service.
