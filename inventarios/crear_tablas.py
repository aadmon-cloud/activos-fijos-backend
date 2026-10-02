# create_tables.py
from app.database import engine
from app import models  # importa tus modelos de SQLAlchemy

models.Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas correctamente")
