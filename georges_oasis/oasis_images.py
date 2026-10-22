"""Register the packaged image manifest with a Flask application."""
import json
from pathlib import Path
from flask import url_for


def init_oasis_images(app):
    """Call once inside create_app(), after configuring app.static_folder."""
    if not app.static_folder:
        raise RuntimeError('Oasis images require an application static folder.')
    path = Path(app.static_folder) / 'images' / 'oasis' / 'manifest.json'
    with path.open(encoding='utf-8') as file:
        assets = json.load(file)['assets']

    def photo_url(key, variant='desktop', external=False):
        """Resolve a new photo key or an existing optimized image filename."""
        filename = (assets[key]['variants'][variant]['path'] if key in assets
                    else 'images/optimized/' + Path(key).stem + '.webp')
        return url_for('static', filename=filename, _external=external)

    @app.context_processor
    def oasis_image_context():
        return {'oasis_images': assets, 'photo_url': photo_url}
