---
name: mila-image-local
description: Make photo-real or stylised character and avatar pictures with local, open-source image models (ComfyUI + Z-Image-Turbo on a Mac, or SSD-1B on a CPU-only box), then steer, check and clean them. Use when a design needs real pictures, not hand-drawn shapes, and online image tools are off or not allowed.
---

# Local image making (open source)

## House rules
- Never delete anything. Each round goes in a new folder.
- Use only open-source models licensed for product use. Check the model card's licence first; skip non-commercial ones (for example EdgeSAM).
- Original people only. Never copy a real person or an example photo, keep characters adult and professional, and keep any "AI" label the product needs.
- Strip hidden data before sharing: `exiftool -all= -overwrite_original <file>`.

## Pick the route
| Machine | Route | Speed |
|---|---|---|
| Mac (Apple silicon) | Comfy Desktop + Z-Image-Turbo (Apache 2.0, `Comfy-Org/Z-Image-Turbo`, ~12 GB smaller set) | fast; check on 16 GB |
| CPU-only Linux | `diffusers` + `segmind/SSD-1B` (Apache 2.0) | ~6-7 min per 768x1024 image on 4 cores |

Keep big models on an external drive when the internal disk is tight.

## Steps
1. Write the description in one short paragraph. CLIP-based models read only ~77 tokens, so put the face first, then the body, then the background.
2. Always add a negative list: `child, doll, chibi, cartoon, text, watermark, logo, nude, revealing, deformed face, extra fingers, blurry`.
3. Make 2-4 seeds, look at them, and keep the best.
4. To steer a good picture (skin tone, face, mood) without losing the body, run image-to-image at strength 0.4-0.5. Above 0.6 it redraws everything.
5. Strip hidden data, save, and write down the design calls (what you picked and why) next to the pictures.

## CPU script
`scripts/make_image.py` takes a prompt, a seed list and an optional starting image:
```
python -I scripts/make_image.py --prompt "..." --seeds 3 17 --out round1
python -I scripts/make_image.py --prompt "..." --init best.png --strength 0.5 --seeds 12 --out round2
```
Install with `pip install torch diffusers transformers accelerate safetensors`.

## Lessons
- Hand-drawn SVG shapes can't reach photo-real. Use a model.
- Pasting a photo face onto a drawn body, then blending, comes out doll-like. Generate the whole figure instead.
- Saying "big head, small body" or "cute" pushes the picture childlike. Avoid those words.
- People react best to pictures they can comment on, so post pictures, not descriptions.
