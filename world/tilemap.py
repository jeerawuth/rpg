# world/tilemap.py
# ระบบ tilemap (placeholder)

class TileMap:
    def __init__(self, map_id: str) -> None:
        self.map_id = map_id
        # TODO: โหลดข้อมูลจาก level_data / JSON

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface, camera_offset) -> None:
        pass
