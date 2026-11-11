"""Regenerate web-sized derivatives without modifying source photographs."""
from pathlib import Path
from PIL import Image, ImageOps

source_dir = Path(__file__).resolve().parent.parent / 'static' / 'images'
output = source_dir / 'optimized'
output.mkdir(exist_ok=True)
for source in source_dir.iterdir():
    if not source.is_file() or source.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        continue
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((1600, 1200))
        image.save(output / (source.stem + '.webp'), 'WEBP', quality=82, method=6)
print(f'Optimized images: {sum(p.stat().st_size for p in output.iterdir()):,} bytes')
