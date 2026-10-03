import os

os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("ENTORNO", "local")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
