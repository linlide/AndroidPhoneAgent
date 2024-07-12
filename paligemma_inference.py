import argparse
import PIL.Image
from transformers import PaliGemmaForConditionalGeneration, PaliGemmaProcessor
import torch
import os
import re
from PIL import ImageDraw, Image
import uuid
import numpy as np

# Constants
COLORS = ['#4285f4', '#db4437', '#f4b400', '#0f9d58', '#e48ef1']

def load_model(model_id):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    model = PaliGemmaForConditionalGeneration.from_pretrained(model_id).eval().to(device)
    processor = PaliGemmaProcessor.from_pretrained(model_id)
    return model, processor, device

def infer(image, text, max_new_tokens, model, processor, device):
    inputs = processor(text=text, images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False
        )
    result = processor.batch_decode(generated_ids, skip_special_tokens=True)
    return result[0][len(text):].lstrip("\n")

def decode_segmentation_mask(seg_indices, box_width, box_height):
    # Convert string indices to integers
    indices = [int(idx) for idx in seg_indices if idx is not None]
    
    # Create a 4x4 grid of the indices
    grid = np.array(indices).reshape(4, 4)
    
    # Upsample to 64x64 using nearest neighbor interpolation
    mask_64 = np.repeat(np.repeat(grid, 16, axis=0), 16, axis=1)
    
    # Resize to box dimensions
    mask = Image.fromarray(mask_64.astype(np.uint8))
    mask = mask.resize((box_width, box_height), Image.NEAREST)
    
    return np.array(mask)

def parse_segmentation(output, image_width, image_height):
    _SEGMENT_DETECT_RE = re.compile(
        r'(.*?)' +
        r'<loc(\d{4})>' * 4 + r'\s*' +
        '(?:%s)?' % (r'<seg(\d{3})>' * 16) +
        r'\s*([^;<>]+)? ?(?:; )?',
    )

    objs = []
    seen = set()
    while output:
        m = _SEGMENT_DETECT_RE.match(output)
        if not m:
            break
        gs = list(m.groups())
        before = gs.pop(0)
        name = gs.pop()
        y1, x1, y2, x2 = [int(x) / 1024 for x in gs[:4]]
        
        y1, x1, y2, x2 = map(round, (y1*image_height, x1*image_width, y2*image_height, x2*image_width))
        seg_indices = gs[4:20]

        # Generate segmentation mask
        box_width, box_height = x2 - x1, y2 - y1
        if all(seg_indices):
            mask = decode_segmentation_mask(seg_indices, box_width, box_height)
        else:
            mask = None
        
        content = m.group()
        if before:
            objs.append(dict(content=before))
            content = content[len(before):]
        while name in seen:
            name = (name or '') + "'"
        seen.add(name)
        objs.append(dict(
            content=content, xyxy=(x1, y1, x2, y2), mask=mask, name=name))
        output = output[len(before) + len(content):]

    if output:
        objs.append(dict(content=output))

    return objs

def process_image(image, text, task, model, processor, device, max_new_tokens=100):
    if task == "generate":
        return infer(image, text, max_new_tokens, model, processor, device)
    elif task in ["segment", "detect"]:
        output = infer(image, f"{task} {text}", max_new_tokens, model, processor, device)
        return parse_segmentation(output, image.width, image.height)
    else:
        raise ValueError(f"Unknown task: {task}")

def save_results(image, results, task, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    if task == "generate":
        output_path = os.path.join(output_dir, f"generated_text_{uuid.uuid4()}.txt")
        with open(output_path, "w") as f:
            f.write(f"Generated text: {results}")
        print(f"Generated text saved to: {output_path}")
    elif task in ["segment", "detect"]:
        output_image = image.copy()
        draw = ImageDraw.Draw(output_image)
        for obj in results:
            if 'xyxy' in obj:
                x1, y1, x2, y2 = obj['xyxy']
                color = COLORS[hash(str(obj.get('name', ''))) % len(COLORS)]
                if obj['mask'] is not None:
                    # Create a colored mask
                    colored_mask = np.array(Image.new('RGB', (x2-x1, y2-y1), color))
                    # Apply the mask
                    masked_area = np.where(obj['mask'][..., None], colored_mask, np.array(output_image.crop((x1, y1, x2, y2))))
                    # Paste the masked area back onto the image
                    output_image.paste(Image.fromarray(masked_area), (x1, y1))
                else:
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                label = str(obj.get('name', 'Unknown'))
                draw.text((x1, y1), label, fill=color)
        output_path = os.path.join(output_dir, f"{task}_result_{uuid.uuid4()}.png")
        output_image.save(output_path)
        print(f"Annotated image saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="PaliGemma Inference Script")
    parser.add_argument("--model_id", type=str, default="google/paligemma-3b-mix-448", help="Model ID to use")
    parser.add_argument("--image_path", type=str, required=True, help="Path to input image")
    parser.add_argument("--text", type=str, required=True, help="Input text prompt")
    parser.add_argument("--task", type=str, choices=["generate", "segment", "detect"], default="generate", help="Task to perform")
    parser.add_argument("--max_new_tokens", type=int, default=100, help="Maximum number of new tokens to generate")
    parser.add_argument("--output_dir", type=str, default="output", help="Directory to save output files")
    args = parser.parse_args()

    model, processor, device = load_model(args.model_id)
    image = PIL.Image.open(args.image_path).convert("RGB")
    
    results = process_image(image, args.text, args.task, model, processor, device, args.max_new_tokens)
    save_results(image, results, args.task, args.output_dir)

if __name__ == "__main__":
    main()