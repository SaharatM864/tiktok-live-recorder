import asyncio
import streamlink

from src.utils.logger_manager import logger
from src.core.interfaces import IRecorder
from src.config import config


class StreamlinkRecorder(IRecorder):
    def __init__(self):
        self._is_recording = False
        self._stop_event = asyncio.Event()
        self._process = None

    def is_recording(self) -> bool:
        return self._is_recording

    def stop_recording(self) -> None:
        if self._is_recording:
            logger.info("Stopping recording...")
            self._stop_event.set()

    async def start_recording(self, user: str, room_id: str, output_path: str) -> None:
        self._is_recording = True
        self._stop_event.clear()

        try:
            # Construct the TikTok Live URL
            url = f"https://www.tiktok.com/@{user}/live"
            logger.info(f"Preparing to record {user} ({room_id}) from {url}")

            # Use streamlink to get streams
            session = streamlink.Streamlink()

            # Set options if needed (e.g. http headers)
            if config.proxy:
                session.set_option("http-proxy", config.proxy)
                session.set_option("https-proxy", config.proxy)

            try:
                streams = session.streams(url)
            except streamlink.NoPluginError:
                logger.error(f"Streamlink: No plugin found for {url}")
                return
            except streamlink.PluginError as e:
                logger.error(f"Streamlink: Plugin error: {e}")
                return

            if not streams:
                logger.warning(f"Streamlink: No streams found for {user}")
                return

            # Select best stream (usually 'best')
            stream_url = streams["best"].url
            logger.info(f"Stream found. Recording to {output_path}")

            # Use ffmpeg to record the stream (more stable than python file write)
            # We run ffmpeg as a subprocess
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite
                "-i",
                stream_url,
                "-c",
                "copy",  # Copy stream without re-encoding
                "-f",
                "mp4",
                "-bsf:a",
                "aac_adtstoasc",  # Fix audio stream
                output_path,
            ]

            # Hide ffmpeg output unless debug
            stdout = asyncio.subprocess.DEVNULL
            stderr = asyncio.subprocess.DEVNULL
            if config.log_level == "DEBUG":
                stdout = None
                stderr = None

            self._process = await asyncio.create_subprocess_exec(
                *cmd, stdout=stdout, stderr=stderr
            )

            # Wait for stop event or process finish
            wait_task = asyncio.create_task(self._stop_event.wait())
            process_task = asyncio.create_task(self._process.wait())

            done, pending = await asyncio.wait(
                [wait_task, process_task], return_when=asyncio.FIRST_COMPLETED
            )

            if wait_task in done:
                # Stop requested
                if self._process.returncode is None:
                    self._process.terminate()
                    try:
                        await asyncio.wait_for(self._process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self._process.kill()

            logger.info(f"Recording finished: {output_path}")

        except Exception as e:
            logger.error(f"Error during recording: {e}")
        finally:
            self._is_recording = False
            self._process = None
