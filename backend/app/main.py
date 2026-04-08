from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from app.api.routes import apps, auth, employees, health, users
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.services import app_catalog_service, app_rights_service

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)

origins = [o.strip() for o in settings.cors_allow_origins.split(',') if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=['*'],
        allow_headers=['*'],
    )

base_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_dir / 'templates'))
app.mount('/static', StaticFiles(directory=str(base_dir / 'static')), name='static')

app.include_router(health.router)
app.include_router(auth.router, prefix='/api')
app.include_router(users.router, prefix='/api')
app.include_router(apps.router, prefix='/api')
app.include_router(employees.router, prefix='/api')


@app.on_event('startup')
def startup_init() -> None:
    # Local sqlite mode is used for quick developer testing.
    if settings.atlas_auth_db_url.startswith('sqlite'):
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            columns = {row[1] for row in conn.execute(text("PRAGMA table_info('AtlasAppAccess')")).fetchall()}
            if 'AccessLevel' not in columns:
                conn.execute(text("ALTER TABLE AtlasAppAccess ADD COLUMN AccessLevel INTEGER NOT NULL DEFAULT 1"))
            if 'AccessLabel' not in columns:
                conn.execute(text("ALTER TABLE AtlasAppAccess ADD COLUMN AccessLabel TEXT NULL"))
            conn.execute(
                text(
                    """
                    UPDATE AtlasAppAccess
                    SET AccessLabel = CASE COALESCE(AccessLevel, 1)
                        WHEN 1 THEN 'Viewer'
                        WHEN 2 THEN 'Contributor'
                        WHEN 3 THEN 'Specialist'
                        WHEN 4 THEN 'Manager'
                        WHEN 5 THEN 'Owner'
                        ELSE 'Custom'
                    END
                    WHERE AccessLabel IS NULL OR TRIM(AccessLabel) = ''
                    """
                )
            )
    with SessionLocal.begin() as session:
        app_rights_service.ensure_default_right_definitions(session)


@app.get('/', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        'login.html',
        {
            'request': request,
            'launcher_apps': app_catalog_service.list_login_launcher_apps(),
        },
    )


@app.get('/login', response_class=HTMLResponse)
@app.get('/Login', response_class=HTMLResponse)
def login_alias_page(request: Request):
    return templates.TemplateResponse(
        'login.html',
        {
            'request': request,
            'launcher_apps': app_catalog_service.list_login_launcher_apps(),
        },
    )


@app.get('/admin', response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse('admin.html', {'request': request})


@app.get('/admin/access-matrix', response_class=HTMLResponse)
def access_matrix_page(request: Request):
    return templates.TemplateResponse('access_matrix.html', {'request': request})


@app.get('/admin/rights-matrix', response_class=HTMLResponse)
def rights_matrix_page(request: Request):
    return templates.TemplateResponse('rights_matrix.html', {'request': request})
