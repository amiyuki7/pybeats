from .app import App, Loading


def main() -> None:
    Game = App(Loading)
    Game.run()


if __name__ == "__main__":
    main()
