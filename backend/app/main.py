from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import auth, employees, health, users
from app.core.logging import configure_logging
from app.core.settings import get_settings

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
app.include_router(employees.router, prefix='/api')


@app.get('/', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.get('/admin', response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse('admin.html', {'request': request})
