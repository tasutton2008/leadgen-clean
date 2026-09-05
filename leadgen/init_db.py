# leadgen/init_db.py
# leadgen/init_db.py

from .database import Base, engine
from .models import Lead

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
