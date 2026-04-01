---
name: gemini-img-gen
description: Generate high-resolution images using Gemini's image generation tool. Use when the user needs to create visual assets, concepts, or specific imagery for a project.
---

# Gemini Image Generation Skill

This skill provides a deterministic way to generate and download high-resolution images via the Gemini web interface.

## Usage

Use the provided Python script to generate an image from a prompt. The script will handle navigation, generation, and downloading.

```powershell
python gemini-img-gen/scripts/generate_gemini_img.py "Your detailed image prompt here" "output\image.png"
```

### Script Details: `scripts/generate_gemini_img.py`

- **Input**: A string containing the image generation prompt.
- **Output Path**: A required local file path where the copied image will be saved.
- **Workflow**:
    1. Navigates to the Gemini web interface.
    2. Uses the "Create Image" tool.
    3. Waits for the generation to complete (approx. 60s).
    4. Copies the resulting image and saves it to the requested local path.
- **Output**: Prints the local path to the downloaded image in the format `RESULT_IMAGE_PATH:<path>`.

## Best Practices

- **Detailed Prompts**: Provide clear, descriptive prompts for better results. Include information about style, lighting, composition, and subject matter.
- **Wait for Completion**: Generation takes time. The script is configured to wait, so do not interrupt the process.
- **Check Results**: Always verify the output path and the generated image to ensure it meets your requirements.
