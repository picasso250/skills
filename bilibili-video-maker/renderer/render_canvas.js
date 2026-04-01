const { createCanvas } = require('canvas');
const fs = require('fs-extra');
const path = require('path');

const ARGS = process.argv.slice(2);
const SEGMENTS_JSON = ARGS[0];
const DURATION_SEC = parseFloat(ARGS[1]);
const OUTPUT_DIR = ARGS[2];
const FPS = 30;

if (!SEGMENTS_JSON || !DURATION_SEC || !OUTPUT_DIR) {
  console.error('Usage: node render_canvas.js <segments.json> <duration_sec> <output_dir>');
  process.exit(1);
}

const WIDTH = 1280;
const HEIGHT = 720;
const CANVAS = createCanvas(WIDTH, HEIGHT);
const CTX = CANVAS.getContext('2d');

const PALETTE = ['#FFD700', '#00FFFF', '#FF69B4', '#ADFF2F', '#FFA500']; // Gold, Cyan, Pink, GreenYellow, Orange

function parseRichText(text) {
  const parts = [];
  const regex = /\*(.*?)\*/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ text: text.substring(lastIndex, match.index), isKeyword: false });
    }
    parts.push({ text: match[1], isKeyword: true });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push({ text: text.substring(lastIndex), isKeyword: false });
  }
  return parts;
}

function drawLine(ctx, line, y, scale) {
  const richParts = parseRichText(line);
  const fontSize = 56;
  const keywordFontSize = 72;
  
  // Calculate total width
  let totalWidth = 0;
  richParts.forEach((p, idx) => {
    ctx.font = `bold ${p.isKeyword ? keywordFontSize : fontSize}px "Microsoft YaHei"`;
    totalWidth += ctx.measureText(p.text).width + (idx < richParts.length - 1 ? 5 : 0);
  });

  let currentX = (WIDTH - totalWidth) / 2;

  richParts.forEach(p => {
    ctx.font = `bold ${p.isKeyword ? keywordFontSize : fontSize}px "Microsoft YaHei"`;
    ctx.fillStyle = p.isKeyword ? PALETTE[0] : 'white';
    
    // Shadow
    ctx.save();
    ctx.shadowColor = 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = 10;
    ctx.shadowOffsetX = 4;
    ctx.shadowOffsetY = 4;
    ctx.fillText(p.text, currentX, y);
    ctx.restore();
    
    // Main Text
    ctx.fillText(p.text, currentX, y);
    currentX += ctx.measureText(p.text).width + 5;
  });
}

async function render() {
  const segments = await fs.readJson(SEGMENTS_JSON);
  const framesDir = path.join(OUTPUT_DIR, 'frames');
  await fs.ensureDir(framesDir);

  const totalFrames = Math.ceil(DURATION_SEC * FPS);
  console.log(`Rendering ${totalFrames} frames...`);

  for (let f = 0; f < totalFrames; f++) {
    const time = f / FPS;
    CTX.fillStyle = 'black';
    CTX.fillRect(0, 0, WIDTH, HEIGHT);

    const segment = segments.find(s => time >= s.start_sec && time <= s.end_sec);

    if (segment) {
      const elapsed = time - segment.start_sec;
      const popDuration = 0.15;
      let scale = 1.0;
      if (elapsed < popDuration) {
        const t = elapsed / popDuration;
        scale = 0.8 + Math.sin(t * Math.PI) * 0.3; 
      }

      CTX.save();
      // Apply scale around the center
      CTX.translate(WIDTH / 2, HEIGHT / 2);
      CTX.scale(scale, scale);
      CTX.translate(-WIDTH / 2, -HEIGHT / 2);

      const lines = segment.text.split('\n');
      const lineHeight = 100;
      const totalTextHeight = lines.length * lineHeight;
      let startY = (HEIGHT - totalTextHeight) / 2 + lineHeight / 2;

      lines.forEach((line, idx) => {
        drawLine(CTX, line, startY + idx * lineHeight, scale);
      });

      CTX.restore();
    }

    const fileName = `frame_${String(f).padStart(5, '0')}.png`;
    await fs.writeFile(path.join(framesDir, fileName), CANVAS.toBuffer('image/png'));
    if (f % 100 === 0) console.log(`Frame ${f}/${totalFrames}`);
  }
  console.log('DONE.');
}

render().catch(console.error);
