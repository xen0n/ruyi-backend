from .root import app as app

# register the various API endpoints
from . import admin as admin
from . import frontend as frontend
from . import misc as misc
from . import news as news
from . import oauth2 as oauth2
from . import packages as packages
from . import releases as releases
from . import repo_telemetry as repo_telemetry
from . import telemetry as telemetry

app.include_router(admin.router)
app.include_router(frontend.router)
app.include_router(misc.router)
app.include_router(news.router)
app.include_router(oauth2.router)
app.include_router(packages.router)
app.include_router(releases.router)
app.include_router(repo_telemetry.router)
app.include_router(telemetry.router)
