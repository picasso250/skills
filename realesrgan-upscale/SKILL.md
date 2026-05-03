---
name: realesrgan-upscale
description: Use Real-ESRGAN or compatible open-source AI upscalers to batch upscale local images, especially when clients complain that faces or fine details look soft. Use for PNG/JPG/WebP image folders, AI illustration upscaling, face-detail delivery checks, and creating a new enlarged output folder without changing identity.
---

# Real-ESRGAN Upscale

## Workflow

1. Inspect source files first: count images, read dimensions, and make an overview/contact sheet with face crops when faces matter.
2. Prefer Real-ESRGAN ncnn-vulkan for local batch work. If the official `Real-ESRGAN-ncnn-vulkan` release lacks bundled models, use the main `xinntao/Real-ESRGAN` release package that includes `models/`.
3. For AI illustration or anime-like images, start with `realesr-animevideov3 -s 2`. For photo-like images, test `realesrgan-x4plus -s 2`.
4. Avoid GFPGAN/CodeFormer unless the user explicitly accepts face reconstruction. They may improve perceived sharpness but can change identity.
5. Always run one sample first, view the full image and face crop, then batch process only after the sample is clean.
6. Save outputs to a new sibling folder, usually `<source>_realesrgan_2x`.
7. Verify output count, dimensions, and obvious artifacts. If block seams or tile scrambling appear, retry with a different model or safer runtime options such as `-j 1:1:1`.

## Command Pattern

```powershell
& "~/tools/realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan.exe" `
  -i "C:\path\input-folder" `
  -o "C:\path\input-folder_realesrgan_2x" `
  -n realesr-animevideov3 `
  -s 2 `
  -f png `
  -j 1:1:1
```

## Judgment

- Do not call an image blurry just because the face is small in the full composition.
- Treat AI upscaling as perceptual enhancement, not mathematically lossless recovery.
- For client wording in Chinese, say that a 2x AI HD super-resolution pass was applied and facial/detail sharpness was enhanced.
