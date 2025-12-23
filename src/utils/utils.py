import json
import os

from utils.enums import Info


def banner() -> None:
    """
    Prints a banner with the name of the tool and its version number.
    """
    print(Info.BANNER, flush=True)


def load_config(filename: str):
    """
    Loads a JSON config file from the project root.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # utils is in src/utils, so project root (where json files are) is ../..
    # Wait, cookies.json is in src/ (based on previous code: os.path.join(script_dir, "..", "cookies.json"))
    # If script_dir is src/utils, then .. is src.
    config_path = os.path.join(script_dir, "..", filename)
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_cookies():
    """
    Loads the cookies.json file.
    """
    return load_config("cookies.json")


def read_telegram_config():
    """
    Loads the telegram.json file.
    """
    return load_config("telegram.json")


def is_termux() -> bool:
    """
    Checks if the script is running in Termux.

    Returns:
        bool: True if running in Termux, False otherwise.
    """
    import distro
    import platform

    return platform.system().lower() == "linux" and distro.like() == ""


def is_windows() -> bool:
    """
    Checks if the script is running on Windows.

    Returns:
        bool: True if running on Windows, False otherwise.
    """
    import platform

    return platform.system().lower() == "windows"


def is_linux() -> bool:
    """
    Checks if the script is running on Linux.

    Returns:
        bool: True if running on Linux, False otherwise.
    """
    import platform

    return platform.system().lower() == "linux"
