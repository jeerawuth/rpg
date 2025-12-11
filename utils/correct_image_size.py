from PIL import Image
import math

IMG = "./input/overworld_level_02.png"  # แก้เป็นไฟล์ของคุณ
img = Image.open(IMG).convert("RGBA")

w, h = img.size
print("old size:", w, h)

new_w = math.ceil(w / 32) * 32
new_h = math.ceil(h / 32) * 32

# สร้างภาพใหม่โปร่งใส (หรือจะใช้สีพื้นก็ได้)
new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))

# วางภาพเดิมที่มุมซ้ายบน (0,0)
new_img.paste(img, (0, 0))

new_img.save("./output/overworld_level_02.png")
print("new size:", new_img.size)
