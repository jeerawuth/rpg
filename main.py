# main.py
# จุดเริ่มต้นของเกม

from core.game_app import GameApp
from scenes.main_menu_scene import MainMenuScene


def main() -> None:
    app = GameApp()
    app.scene_manager.set_scene(MainMenuScene(app))
    app.run()


if __name__ == "__main__":
    main()
