"""Explicit setup, recovery, queue and maintenance commands."""
from datetime import timedelta
from pathlib import Path
import json
import click
from flask import current_app
from werkzeug.security import generate_password_hash
from .models import (db, StaffUser, AuditEvent, InquiryAttempt, LoginAttempt,
                     RateBucket, utcnow, MediaAsset)


def register_commands(app):
    @app.cli.command('import-catalog')
    @click.option('--dry-run', is_flag=True)
    def import_catalog_command(dry_run):
        from .content import load_content, validate_content
        from .services.catalog import import_catalog
        data = load_content()
        issues = validate_content(data)
        if issues:
            raise click.ClickException('\n'.join(issues))
        try:
            result = import_catalog(data, dry_run)
        except ValueError as exc:
            db.session.rollback()
            raise click.ClickException(str(exc)) from exc
        click.echo(f"{'Would import' if dry_run else 'Imported'} {result['created']} records; {result['items']} menu items. Price visibility preserved.")

    @app.cli.command('staff-user')
    @click.argument('username')
    @click.option('--role', type=click.Choice(['owner', 'editor', 'inquiry']), default='owner')
    @click.option('--name', default='')
    @click.password_option(confirmation_prompt=True)
    def staff_user(username, role, name, password):
        username = username.strip().casefold()
        if not username or len(username) > 80 or len(name) > 100 or not 15 <= len(password) <= 256:
            raise click.ClickException('Use a username up to 80 characters and passphrase between 15 and 256 characters.')
        if app.config['PRODUCTION'] and (username == 'username' or password == 'password'):
            raise click.ClickException('Demo credentials are prohibited in production.')
        user = db.session.scalar(db.select(StaffUser).where(StaffUser.username == username))
        if user:
            user.session_version += 1
        else:
            user = StaffUser(username=username, display_name=name or username)
            db.session.add(user)
        user.password_hash, user.role, user.active = generate_password_hash(password), role, True
        if name:
            user.display_name = name
        db.session.add(AuditEvent(actor='operator-cli', action='staff.provision', entity=username, summary=role))
        db.session.commit()
        click.echo('Named staff account saved. Previous sessions were revoked.')

    @app.cli.command('process-notifications')
    @click.option('--limit', default=25, type=click.IntRange(1, 100))
    @click.option('--watch', is_flag=True, help='Poll once a second; run under a process supervisor.')
    def notifications(limit, watch):
        from .services.notifications import drain
        import time
        while True:
            processed = drain(limit)
            if processed or not watch:
                click.echo(f'Processed {processed} notification jobs.')
            if not watch:
                break
            time.sleep(1)

    @app.cli.command('backend-cleanup')
    def cleanup():
        import time
        cutoff = utcnow() - timedelta(days=1)
        for model in (InquiryAttempt, LoginAttempt):
            db.session.execute(db.delete(model).where(model.attempted_at < cutoff))
        db.session.execute(db.delete(RateBucket).where(RateBucket.window < int(time.time()) // 900 - 96))
        known = {item for asset in db.session.scalars(db.select(MediaAsset)) for item in (v['filename'] for v in asset.variants.values())}
        folder = Path(app.instance_path) / 'media'
        if folder.exists():
            for path in folder.glob('*.webp'):
                if path.name not in known and path.stat().st_mtime < time.time() - 86400:
                    path.unlink()
        db.session.commit()
        click.echo('Expired abuse counters and abandoned media cleaned. Inquiry records were preserved.')
