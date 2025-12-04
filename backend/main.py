import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.db import Base, engine


app = create_app()


def init_db():
    Base.metadata.create_all(bind=engine)


init_db()


