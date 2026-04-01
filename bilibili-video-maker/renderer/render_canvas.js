const { createCanvas, registerFont } = require('canvas');
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

async function render() {
  const segments = await fs.readJson(SEGMENTS_JSON);
  const framesDir = path.join(OUTPUT_DIR, 'frames');
  await fs.ensureDir(framesDir);

  const totalFrames = Math.ceil(DURATION_SEC * FPS);
  console.log(`Total frames to render: ${totalFrames} (${DURATION_SEC}s @ ${FPS}fps)`);

  for (let f = 0; f < totalFrames; f++) {
    const time = f / FPS;
    
    // Clear canvas
    CTX.fillStyle = 'black';
    CTX.fillRect(0, 0, WIDTH, HEIGHT);

    // Find active segment
    const segment = segments.find(s => time >= s.start_sec && time <= s.end_sec);

    if (segment) {
      const elapsed = time - segment.start_sec;
      const popDuration = 0.15; // Animation duration in seconds
      
      // Calculate scale (Pop-up effect: 0.8 -> 1.1 -> 1.0)
      let scale = 1.0;
      if (elapsed < popDuration) {
        const t = elapsed / popDuration;
        // Ease out back-ish: start small, peak slightly over 1, settle at 1
        scale = 0.8 + Math.sin(t * Math.PI) * 0.3; 
      }

      CTX.save();
      CTX.translate(WIDTH / 2, HEIGHT / 2);
      CTX.scale(scale, scale);
      
      // Draw Text
      CTX.font = 'bold 48px "Microsoft YaHei"'; // Fallback to system font
      CTX.textAlign = 'center';
      CTX.textBaseline = 'middle';
      
      // Shadow
      CTX.fillStyle = 'rgba(0,0,0,0.5)';
      CTX.fillText(segment.text, 4, 4);
      
      // Main Text
      CTX.fillStyle = 'white';
      CTX.fillText(segment.text, 0, 0);
      
      CTX.restore();
    }

    const fileName = `frame_${String(f).padStart(5, '0')}.png`;
    const buffer = CANVAS.toBuffer('image/png');
    await fs.writeFile(path.join(framesDir, fileName), buffer);

    if (f % 100 === 0) console.log(`Rendered frame ${f}/${totalFrames}`);
  }

  console.log('SUCCESS: All frames rendered.');
}

render().catch(err => {
  console.error(err);
  process.exit(1);
});
