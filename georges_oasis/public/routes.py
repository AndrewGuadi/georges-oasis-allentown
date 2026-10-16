from datetime import datetime, timezone
from flask import current_app, abort, make_response, redirect, render_template, request, session, url_for
from . import public_bp
from .sitemap import PAGES, LEGACY
from ..content import public_content, clock_time, money
from ..inquiries import FLEXIBILITY, INTERESTS, OCCASIONS, form_values, new_submission_token, submit_inquiry
from ..models import db, homepage_promotions, current_promotions, Inquiry

public_bp.add_app_template_filter(money, 'money')
public_bp.add_app_template_filter(clock_time, 'clock_time')

@public_bp.context_processor
def site_context():
    return {"site_pages":PAGES,"current_year":datetime.now(timezone.utc).year,**public_content()}

@public_bp.get("/")
def home():
    response = make_response(render_template("public/homepage.html",**homepage_promotions()))
    response.headers['Cache-Control'] = 'no-cache'
    return response

def page_view(page):
    def view():
        context = {"page":page}
        if page["key"] == "specials":
            context.update(current_promotions())
        if page["key"] == "gatherings":
            values = {"contact_method":"email","date_flexibility":"Not sure yet","interests":[request.args['interest']] if request.args.get('interest') in INTERESTS else []}
            errors, status = {},200
            if request.method == "POST":
                values = form_values()
                inquiry,errors,status = submit_inquiry(values)
                if inquiry:
                    return redirect(url_for('public.inquiry_received',reference=inquiry.reference),code=303)
                if 'form' in errors and 'expired' in errors['form']:
                    values['submission_token'] = new_submission_token()
            values.setdefault('submission_token',new_submission_token())
            context.update(values=values,errors=errors,occasions=OCCASIONS,interests=INTERESTS,flexibilities=FLEXIBILITY)
            response = make_response(render_template('public/gatherings.html',**context),status)
            response.headers['Cache-Control'] = 'no-store'
            return response
        response = make_response(render_template(f"public/{page['key']}.html",**context))
        response.headers['Cache-Control'] = 'no-cache'
        return response
    return view

for page in PAGES:
    public_bp.add_url_rule(page['path'],endpoint=page['key'],view_func=page_view(page),methods=['GET','POST'] if page['key']=='gatherings' else ['GET'])

@public_bp.get('/inquiry-received/<reference>')
def inquiry_received(reference):
    if reference not in session.get('inquiry_receipts',[]):
        abort(404)
    if not db.session.execute(db.select(Inquiry.id).filter_by(reference=reference)).scalar_one_or_none():
        abort(404)
    response = make_response(render_template('public/inquiry_received.html',reference=reference))
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['Cache-Control'] = 'no-store'
    return response

def legacy_view(endpoint):
    def view():
        target=url_for('public.'+endpoint)
        if request.query_string:
            target+='?'+request.query_string.decode('utf-8',errors='replace')
        return redirect(target,code=301)
    return view

for index,(path,endpoint) in enumerate(LEGACY.items()):
    public_bp.add_url_rule(path,endpoint=f'legacy_{index}',view_func=legacy_view(endpoint))

@public_bp.get('/sitemap.xml')
def sitemap_xml():
    response=make_response(render_template('public/sitemap.xml',pages=PAGES))
    response.headers['Content-Type']='application/xml'
    return response

@public_bp.get('/robots.txt')
def robots():
    if not current_app.config['PRODUCTION']:
        return 'User-agent: *\nDisallow: /\n', 200, {'Content-Type':'text/plain'}
    return 'User-agent: *\nDisallow: /admin\nDisallow: /inquiry-received/\nSitemap: '+url_for('public.sitemap_xml',_external=True)+'\n',200,{'Content-Type':'text/plain'}
