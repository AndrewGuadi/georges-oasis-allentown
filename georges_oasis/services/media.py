"""Validated immutable image derivatives on persistent local storage."""
from pathlib import Path
from uuid import uuid4
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from ..models import MediaAsset, db


def upload_image(upload, alt, caption='', source='Staff upload'):
    if not alt or len(alt) > 300 or len(caption) > 500 or len(source) > 300:
        raise ValueError('Describe the image in at most 300 characters; caption up to 500.')
    stream = upload.stream
    stream.seek(0, 2)
    length = stream.tell()
    stream.seek(0)
    if length > 4 * 1024 * 1024:
        raise ValueError('Choose a file smaller than 4 MiB.')
    key = uuid4().hex
    folder = Path(current_app.instance_path) / 'media'
    folder.mkdir(exist_ok=True)
    written = []
    try:
        with Image.open(stream) as original:
            if original.format not in ('JPEG', 'PNG', 'WEBP') or getattr(original, 'n_frames', 1) != 1 or original.width * original.height > 20_000_000:
                raise ValueError('Choose a single-frame JPG, PNG or WebP under 20 megapixels.')
            original.load()
            picture = ImageOps.exif_transpose(original).convert('RGB')
            variants = {}
            for width in (400, 800, 1600):
                output = picture.copy()
                output.thumbnail((width, width))
                filename = f'{key}-{width}.webp'
                path = folder / filename
                output.save(path, 'WEBP', quality=85)
                written.append(path)
                variants[str(width)] = {'filename': filename, 'width': output.width, 'height': output.height}
        asset = MediaAsset(id=key, alt=alt, caption=caption, source=source, variants=variants)
        db.session.add(asset)
        return asset
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        for path in written:
            path.unlink(missing_ok=True)
        raise ValueError('The image could not be decoded safely.') from error
