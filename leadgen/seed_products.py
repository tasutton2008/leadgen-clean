from .database import SessionLocal
from .models import Product

db = SessionLocal()
recommended_products = db.query(Product).limit(3).all()
db.close()

products = [
    Product(
        name="All-Purpose Cleaner",
        description="Multi-surface cleaning solution.",
        price="$15.00",
        image="all_purpose_cleaner.jpg",
        category="Commercial"
    ),
    Product(
        name="Disinfectant Spray",
        description="Kills 99.9% of germs.",
        price="$30.00",
        image="disinfectant_spray.jpg",
        category="Medical"
    ),
    Product(
        name="Floor Degreaser",
        description="Heavy-duty commercial degreaser.",
        price="$19.99",
        image="floor_degreaser.jpg",
        category="Industrial"
    ),
]

db.add_all(products)
db.commit()
db.close()

print("Products seeded.")
