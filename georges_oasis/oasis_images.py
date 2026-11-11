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
    app.extensions['oasis_assets'] = assets

    def photo_url(key, variant='desktop', external=False):
        """Resolve a new photo key or an existing optimized image filename."""
        if key and key.startswith('upload:'):
            return url_for('backend.media_file', media_id=key[7:], size='1600', _external=external)
        filename = (assets[key]['variants'][variant]['path'] if key in assets
                    else 'images/optimized/' + Path(key).stem + '.webp')
        return url_for('static', filename=filename, _external=external)

    @app.context_processor
    def oasis_image_context():
        return {'oasis_images': assets, 'photo_url': photo_url}
