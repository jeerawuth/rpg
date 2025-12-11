from PIL import Image

# ---- ตั้งค่าตรงนี้ ----
INPUT_FILE = "./input/overworld_level_05.png"     # ชื่อไฟล์ต้นฉบับ
OUTPUT_FILE = "./output/overworld_level_05_resized.png"  # ชื่อไฟล์หลังย่อ
SCALE_PERCENT = 50           # เปอร์เซ็นต์ที่ต้องการ เช่น 50 = ลดเหลือ 50%
# -----------------------

# เปิดรูป
img = Image.open(INPUT_FILE)

# ขนาดเดิม
orig_w, orig_h = img.size
print("Original size:", orig_w, "x", orig_h)

# คำนวณขนาดใหม่จากเปอร์เซ็นต์
scale = SCALE_PERCENT / 100.0
new_w = int(orig_w * scale)
new_h = int(orig_h * scale)

# ย่อรูป (รักษาอัตราส่วนเดิม)
resized = img.resize((new_w, new_h), Image.LANCZOS)

# บันทึก
resized.save(OUTPUT_FILE)
print("Saved:", OUTPUT_FILE, "size:", new_w, "x", new_h)
