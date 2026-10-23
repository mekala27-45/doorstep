"""ASGI entry point: `uvicorn doorstep_api.main:app`."""

from doorstep_api.app import create_app

app = create_app()
