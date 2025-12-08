from PIL import Image

IMG = "./input/overworld_level_21.png"  # แก้เป็นไฟล์ของคุณ
img = Image.open(IMG).convert("RGBA")

w, h = img.size
print("old size:", w, h)

NEW_W, NEW_H = 3840, 1120

# สร้างภาพใหม่โปร่งใส (หรือจะใช้สีพื้นก็ได้)
new_img = Image.new("RGBA", (NEW_W, NEW_H), (0, 0, 0, 0))

# วางภาพเดิมที่มุมซ้ายบน (0,0)
new_img.paste(img, (0, 0))

new_img.save("./output/overworld_level_10.png")
print("new size:", new_img.size)
