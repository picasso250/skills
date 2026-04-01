const { createCanvas } = require('canvas');
const fs = require('fs-extra');
const path = require('path');

const ARGS = process.argv.slice(2);
const SEGMENTS_JSON = ARGS[0];
const DURATION_SEC = parseFloat(ARGS[1]);
const OUTPUT_DIR = ARGS[2];
const FPS = 30;

const WIDTH = 1280;
const HEIGHT = 720;
const CANVAS = createCanvas(WIDTH, HEIGHT);
const CTX = CANVAS.getContext('2d');

const PALETTE = ['#FFD700', '#00FFFF', '#FF69B4', '#ADFF2F', '#FFA500', '#00FF7F'];

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

function drawLine(ctx, line, y, segmentIdx) {
  const richParts = parseRichText(line);
  const fontSize = 52;
  const keywordFontSize = 68;
  
  // Calculate total width
  let totalWidth = 0;
  richParts.forEach((p) => {
    ctx.font = `bold ${p.isKeyword ? keywordFontSize : fontSize}px "Microsoft YaHei"`;
    totalWidth += ctx.measureText(p.text).width + 5;
  });

  let currentX = (WIDTH - totalWidth) / 2;
  let keywordIdx = 0;

  richParts.forEach(p => {
    ctx.font = `bold ${p.isKeyword ? keywordFontSize : fontSize}px "Microsoft YaHei"`;
    
    // Each keyword in a segment can have a different color from PALETTE
    if (p.isKeyword) {
      ctx.fillStyle = PALETTE[(segmentIdx + keywordIdx) % PALETTE.length];
      keywordIdx++;
    } else {
      ctx.fillStyle = 'white';
    }
    
    // Shadow for readability
    ctx.save();
    ctx.shadowColor = 'black';
    ctx.shadowBlur = 8;
    ctx.shadowOffsetX = 3;
    ctx.shadowOffsetY = 3;
    ctx.fillText(p.text, currentX, y);
    ctx.restore();
    
    ctx.fillText(p.text, currentX, y);
    currentX += ctx.measureText(p.text).width + 5;
  });
}

async function render() {
  const segments = await fs.readJson(SEGMENTS_JSON);
  const framesDir = path.join(OUTPUT_DIR, 'frames');
  await fs.ensureDir(framesDir);
  await fs.emptyDir(framesDir); 

  const totalFrames = Math.floor(DURATION_SEC * FPS); // Match FFmpeg's likely interpretation
  console.log(`Rendering ${totalFrames} frames for ${DURATION_SEC}s @ ${FPS}fps...`);

  for (let f = 0; f < totalFrames; f++) {
    const time = f / FPS;
    CTX.fillStyle = 'black';
    CTX.fillRect(0, 0, WIDTH, HEIGHT);

    // Find active segment with a tiny epsilon to handle floating point edges
    const segmentIdx = segments.findIndex(s => time >= (s.start_sec - 0.001) && time <= (s.end_sec + 0.001));

    if (segmentIdx !== -1) {
      const segment = segments[segmentIdx];
      const elapsed = Math.max(0, time - segment.start_sec);
      const popDuration = 0.12;
      let scale = 1.0;
      if (elapsed < popDuration) {
        const t = elapsed / popDuration;
        scale = 0.85 + Math.sin(t * Math.PI) * 0.25; 
      }

      CTX.save();
      CTX.translate(WIDTH / 2, HEIGHT / 2);
      CTX.scale(scale, scale);
      CTX.translate(-WIDTH / 2, -HEIGHT / 2);

      const lines = segment.text.split('\n');
      const lineHeight = 100;
      const totalTextHeight = lines.length * lineHeight;
      let startY = (HEIGHT - totalTextHeight) / 2 + (lineHeight * 0.7);

      lines.forEach((line, idx) => {
        drawLine(CTX, line, startY + idx * lineHeight, segmentIdx);
      });

      CTX.restore();
    }

    const fileName = `frame_${String(f).padStart(5, '0')}.png`;
    await fs.writeFile(path.join(framesDir, fileName), CANVAS.toBuffer('image/png'));
    if (f % 100 === 0) console.log(`Frame ${f}/${totalFrames}`);
  }
  console.log('DONE.');
}

render().catch(err => {
  console.error(err);
  process.exit(1);
});
