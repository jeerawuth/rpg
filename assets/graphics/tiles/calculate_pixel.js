const { createCanvas, loadImage } = require("canvas");

const TILE_SIZE = 32;
const IMG_PATH = "overworld_rock_tiles_no_grid.png";   // ชื่อรูปกำแพงจริง

async function main() {
  const img = await loadImage(IMG_PATH);
  const width = img.width;
  const height = img.height;

  const tilesX = width / TILE_SIZE;   // 64
  const tilesY = height / TILE_SIZE;  // 36

  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);

  const ground   = [];
  const details  = [];
  const collision = [];

  for (let ty = 0; ty < tilesY; ty++) {
    const gRow = new Array(tilesX).fill(0);
    const dRow = new Array(tilesX).fill(0);
    const cRow = new Array(tilesX).fill(0);

    for (let tx = 0; tx < tilesX; tx++) {
      const x0 = tx * TILE_SIZE;
      const y0 = ty * TILE_SIZE;

      const imageData = ctx.getImageData(x0, y0, TILE_SIZE, TILE_SIZE).data;

      let hasWall = false;
      for (let i = 0; i < imageData.length; i += 4) {
        const alpha = imageData[i + 3];
        if (alpha !== 0) {  // มีพิกเซลที่ไม่โปร่งใส → มีกำแพง
          hasWall = true;
          break;
        }
      }

      if (hasWall) {
        dRow[tx] = 1;  // index tile กำแพง (ตอนนี้ให้เป็น 1)
        cRow[tx] = 1;  // ชนได้
      }
    }

    ground.push(gRow);      // ทั้ง map = 0
    details.push(dRow);
    collision.push(cRow);
  }

  // พิมพ์ JSON ที่พร้อมเอาไปใส่ใน level01.json เลย
  const layers = { ground, details, collision };
  console.log(JSON.stringify(layers, null, 2));
}

main().catch(err => console.error(err));
