from pathlib import Path
from pygame import DOUBLEBUF


class Conf:
    FLAGS = DOUBLEBUF

    SOUND_BUFFER_SIZE = 1024

    MIXER_CHANNELS = 32

    TARGET_FPS = 60

    # This is the best for a 2020 M1 MacBook Air 8GB
    MAX_ALLOWED_THREADS = 30

    # These are all 16:9 aspect ratio. Take it or leave it.
    SUPPORTED_RESOLUTIONS = [
        {"width": 960, "height": 540},
        {"width": 1280, "height": 720},
        {"width": 1366, "height": 768},
        {"width": 1600, "height": 900},
        {"width": 1920, "height": 1080},
        {"width": 2560, "height": 1440},
    ]

    ROOT_DIR = Path(__file__).resolve().parents[2]

    KEYBINDS = {
        "lane0": "a",
        "lane1": "s",
        "lane2": "d",
        "lane3": "f",
        "lane4": "j",
        "lane5": "k",
        "lane6": "l",
        "lane7": ";",
    }

    # LANGUAGE: Literal["JP", "EN"] = "EN"

    class JP:
        song_name = "【曲名】"
        prod = "【作曲】"
        vocals = "【歌】"
        mapper = "【ビートマップ】"

    class EN:
        song_name = "Song Name: "
        prod = "Music By: "
        vocals = "Vocals: "
        mapper = "Mapped By: "

    text = JP
