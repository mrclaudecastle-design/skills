"""Make images locally with an open-source SDXL-family model (default: segmind/SSD-1B, Apache 2.0).

Text-to-image, or image-to-image when --init is given. Never overwrites: each run writes to a new folder.
"""
import argparse, os, time

import torch
from diffusers import StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
from PIL import Image

NEG = ("child, kid, doll, chibi, cartoon, anime, text, watermark, logo, nude, revealing, "
       "deformed face, extra limbs, extra fingers, blurry")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default=NEG)
    ap.add_argument("--model", default="segmind/SSD-1B")
    ap.add_argument("--seeds", type=int, nargs="+", default=[7])
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--guidance", type=float, default=7.0)
    ap.add_argument("--init", help="starting image for image-to-image")
    ap.add_argument("--strength", type=float, default=0.5)
    ap.add_argument("--out", required=True, help="new output folder (must not exist)")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=False)  # never overwrite an earlier round
    torch.set_num_threads(os.cpu_count() or 4)
    kw = dict(torch_dtype=torch.float32, use_safetensors=True)
    if a.init:
        pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(a.model, **kw)
        init = Image.open(a.init).convert("RGB")
    else:
        pipe = StableDiffusionXLPipeline.from_pretrained(a.model, **kw)

    for seed in a.seeds:
        t = time.time()
        g = torch.Generator().manual_seed(seed)
        common = dict(prompt=a.prompt, negative_prompt=a.negative, num_inference_steps=a.steps,
                      guidance_scale=a.guidance, generator=g)
        if a.init:
            img = pipe(image=init, strength=a.strength, **common).images[0]
        else:
            img = pipe(width=a.width, height=a.height, **common).images[0]
        path = os.path.join(a.out, f"seed-{seed}.png")
        img.save(path)
        print(path, f"{time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
