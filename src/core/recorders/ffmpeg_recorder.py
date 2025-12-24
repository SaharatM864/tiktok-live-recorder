import asyncio
import os
from typing import Optional

from core.interfaces import IRecorder
from utils.logger_manager import logger


class FFmpegRecorder(IRecorder):
    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._is_recording = False
        self._stop_event = asyncio.Event()

    def is_recording(self) -> bool:
        return self._is_recording

    async def stop_recording(self) -> None:
        if not self._is_recording:
            return

        logger.info("Stopping recording...")
        self._stop_event.set()

        if self._process:
            try:
                # Try graceful termination by sending 'q' to stdin (FFmpeg standard quit)
                if self._process.returncode is None:
                    try:
                        if self._process.stdin:
                            self._process.stdin.write(b"q")
                            await self._process.stdin.drain()
                    except Exception:
                        pass

                    try:
                        await asyncio.wait_for(self._process.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        # If 'q' didn't work, try terminate (SIGTERM)
                        logger.warning(
                            "FFmpeg did not quit with 'q', sending terminate..."
                        )
                        self._process.terminate()
                        try:
                            await asyncio.wait_for(self._process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.warning("FFmpeg did not terminate, killing...")
                            self._process.kill()
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")

    async def start_recording(self, stream_url: str, output_path: str) -> None:
        """
        Start recording using FFmpeg directly from the stream URL.
        """
        if self._is_recording:
            logger.warning("Recording already in progress")
            return

        self._is_recording = True
        self._stop_event.clear()

        # Define tasks variables outside try block to ensure visibility in finally
        stop_task = None
        process_task = None

        try:
            # Ensure directory exists
            dirname = os.path.dirname(output_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                stream_url,
                "-c",
                "copy",
                "-f",
                "mp4",
                "-bsf:a",
                "aac_adtstoasc",
                output_path,
            ]

            logger.info(f"Starting FFmpeg recording to {output_path}")

            # Create subprocess
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            # Create tasks
            stop_task = asyncio.create_task(self._stop_event.wait())
            process_task = asyncio.create_task(self._process.wait())

            # Wait for either stop event or process exit
            done, pending = await asyncio.wait(
                [stop_task, process_task], return_when=asyncio.FIRST_COMPLETED
            )

            # If process finished on its own (e.g. stream ended)
            if process_task in done:
                return_code = process_task.result()
                if return_code != 0:
                    _, stderr = await self._process.communicate()
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error(
                        f"FFmpeg exited with error code {return_code}: {error_msg}"
                    )
                else:
                    logger.info("FFmpeg process finished successfully")

            # If stop was requested
            elif stop_task in done:
                await self.stop_recording()

        except Exception as e:
            logger.error(f"Error in FFmpegRecorder: {e}")
        finally:
            # Critical Fix: Cancel any pending tasks to avoid 'Task was destroyed but it is pending'
            if stop_task and not stop_task.done():
                stop_task.cancel()
                try:
                    await stop_task
                except asyncio.CancelledError:
                    pass

            if process_task and not process_task.done():
                process_task.cancel()
                try:
                    await process_task
                except asyncio.CancelledError:
                    pass

            self._is_recording = False
            self._process = None
