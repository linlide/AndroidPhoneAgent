import argparse
import PIL.Image
from transformers import PaliGemmaForConditionalGeneration, PaliGemmaProcessor
import torch

def load_model(model_id):
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    
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

def main():
    parser = argparse.ArgumentParser(description="PaliGemma Inference Script")
    parser.add_argument("--model_id", type=str, default="google/paligemma-3b-mix-448", help="Model ID to use")
    parser.add_argument("--image_path", type=str, required=True, help="Path to input image")
    parser.add_argument("--text", type=str, required=True, help="Input text prompt")
    parser.add_argument("--max_new_tokens", type=int, default=20, help="Maximum number of new tokens to generate")
    args = parser.parse_args()

    model, processor, device = load_model(args.model_id)
    image = PIL.Image.open(args.image_path).convert("RGB")
    
    output = infer(image, args.text, args.max_new_tokens, model, processor, device)
    print(f"Input: {args.text}")
    print(f"Output: {output}")

if __name__ == "__main__":
    main()