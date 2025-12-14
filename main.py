# main.py
# จุดเริ่มต้นของเกม

from core.game_app import GameApp

def main() -> None:
    app = GameApp()
    # รอให้ระบบพร้อมก่อนค่อยโหลดเกม
    from scenes.main_menu_scene import MainMenuScene
    app.scene_manager.set_scene(MainMenuScene(app))
    app.run()


if __name__ == "__main__":
    main()


