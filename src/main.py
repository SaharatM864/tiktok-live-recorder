import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import asyncio


def run_recordings(args, mode, cookies):
    async def _run():
        if isinstance(args.user, list):
            tasks = []
            for user in args.user:
                # Create a recorder for each user
                # Note: We need to instantiate TikTokRecorder for each user
                # But TikTokRecorder class design seems to handle one user at a time or followers mode
                # Let's check how it was initialized before.
                # Before: multiprocessing.Process(target=record_user, args=...)
                # record_user created a new TikTokRecorder instance.

                # We can run them as concurrent tasks
                tasks.append(
                    record_user(
                        user,
                        args.url,
                        args.room_id,
                        mode,
                        args.automatic_interval,
                        args.proxy,
                        args.output,
                        args.duration,
                        cookies,
                    )
                )

            await asyncio.gather(*tasks)
        else:
            await record_user(
                args.user,
                args.url,
                args.room_id,
                mode,
                args.automatic_interval,
                args.proxy,
                args.output,
                args.duration,
                cookies,
            )

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


async def record_user(
    user, url, room_id, mode, interval, proxy, output, duration, cookies
):
    from core.tiktok_recorder import TikTokRecorder
    from utils.logger_manager import logger

    try:
        recorder = TikTokRecorder(
            url=url,
            user=user,
            room_id=room_id,
            mode=mode,
            automatic_interval=interval,
            cookies=cookies,
            proxy=proxy,
            output=output,
            duration=duration,
        )
        await recorder.run()
    except Exception as e:
        logger.error(f"{e}")


def main():
    from utils.args_handler import validate_and_parse_args
    from utils.utils import read_cookies
    from utils.logger_manager import logger
    from utils.custom_exceptions import TikTokRecorderError

    try:
        # validate and parse command line arguments
        args, mode = validate_and_parse_args()

        # read cookies from the config file
        cookies = read_cookies()

        # run the recordings based on the parsed arguments
        run_recordings(args, mode, cookies)

    except TikTokRecorderError as ex:
        logger.error(f"Application Error: {ex}")

    except Exception as ex:
        logger.critical(f"Generic Error: {ex}", exc_info=True)


if __name__ == "__main__":
    # print the banner
    from utils.utils import banner

    banner()

    # check and install dependencies
    from utils.dependencies import check_and_install_dependencies

    check_and_install_dependencies()

    # set up signal handling for graceful shutdown
    # multiprocessing.freeze_support() # Not needed for asyncio

    from utils.signals import setup_signal_handlers

    setup_signal_handlers()

    # run
    main()
