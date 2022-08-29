from .app import App
from .states.loading import Loading


def main() -> None:
    Game = App(Loading)
    Game.run()


if __name__ == "__main__":
    main()
