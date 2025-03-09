# app/main.py
from fastapi import FastAPI
from app.routers import agents
from app.models.models import Base
from app.core.database import engine

def create_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Builder")

# Registrar enrutadores
app.include_router(agents.router)

@app.on_event("startup")
def on_startup():

    create_tables()

