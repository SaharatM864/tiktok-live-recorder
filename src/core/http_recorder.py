import os
import time
from http.client import HTTPException
from requests import RequestException

from utils.logger_manager import logger
from utils.custom_exceptions import LiveNotFound
from utils.enums import TikTokError, Error, TimeOut, Mode
from utils.signals import stop_event


class HttpRecorder:
    """
    Handles the recording of TikTok live streams using HTTP requests.
    """

    def __init__(self, tiktok_api, output_dir, duration=None):
        self.tiktok = tiktok_api
        self.output_dir = output_dir
        self.duration = duration

    def record(self, user, room_id, mode=None):
        """
        Records the live stream to a file.
        Returns the path to the recorded file if successful, None otherwise.
        """
        live_url = self.tiktok.get_live_url(room_id)
        if not live_url:
            raise LiveNotFound(TikTokError.RETRIEVE_LIVE_URL)

        current_date = time.strftime("%Y.%m.%d_%H-%M-%S", time.localtime())

        # Handle output directory path
        output_path = self.output_dir
        if isinstance(output_path, str) and output_path != "":
            if not (output_path.endswith("/") or output_path.endswith("\\")):
                if os.name == "nt":
                    output_path = output_path + "\\"
                else:
                    output_path = output_path + "/"

        filename = (
            f"{output_path if output_path else ''}TK_{user}_{current_date}_flv.mp4"
        )

        if self.duration:
            logger.info(f"Started recording for {self.duration} seconds ")
        else:
            logger.info("Started recording...")

        buffer_size = 512 * 1024  # 512 KB buffer
        buffer = bytearray()

        logger.info("[PRESS CTRL + C ONCE TO STOP]")

        try:
            with open(filename, "wb") as out_file:
                stop_recording = False
                while not stop_recording and not stop_event.is_set():
                    try:
                        if not self.tiktok.is_room_alive(room_id):
                            logger.info("User is no longer live. Stopping recording.")
                            break

                        start_time = time.time()
                        for chunk in self.tiktok.download_live_stream(live_url):
                            buffer.extend(chunk)
                            if len(buffer) >= buffer_size:
                                out_file.write(buffer)
                                buffer.clear()

                            elapsed_time = time.time() - start_time
                            if self.duration and elapsed_time >= self.duration:
                                stop_recording = True
                                break

                    except ConnectionError:
                        if mode == Mode.AUTOMATIC:
                            logger.error(Error.CONNECTION_CLOSED_AUTOMATIC)
                            time.sleep(TimeOut.CONNECTION_CLOSED * TimeOut.ONE_MINUTE)
                        else:
                            raise  # Re-raise if not automatic? Or handle same?

                    except (RequestException, HTTPException):
                        time.sleep(2)

                    except KeyboardInterrupt:
                        logger.info("Recording stopped by user.")
                        stop_recording = True

                    except Exception as ex:
                        logger.error(f"Unexpected error: {ex}\n")
                        stop_recording = True

                    finally:
                        if buffer:
                            out_file.write(buffer)
                            buffer.clear()
                        out_file.flush()

            logger.info(f"Recording finished: {filename}\n")
            return filename

        except Exception as e:
            logger.error(f"Error creating output file: {e}")
            return None
