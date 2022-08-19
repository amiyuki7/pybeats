class Meta:
    name: str = ""
    name_en: str = ""

    prod: str = ""
    prod_en: str = ""

    song_path: str = ""
    lite_song_path: str = ""

    lite_img: str = ""

    class Vocals:
        vocaloid: str = ""
        vocaloid_en: str = ""
        vocaloid_avatar: str = ""

        cover: str = ""
        cover_en: str = ""
        cover_avatar: str = ""

    vocals = Vocals

    class Mv:
        available: bool = True
        frames_path: str = ""

    mv = Mv

    mature: bool = True

    class Difficulty:
        easy: int = 4
        normal: int = 11
        hard: int = 17
        expert: int = 23
        master: int = 27

    difficulty = Difficulty
