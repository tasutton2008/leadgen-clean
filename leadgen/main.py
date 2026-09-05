# leadgen/main.py
from itertools import product
import os
print("LOADED FILE:", os.path.abspath(__file__))

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import get_db, SessionLocal
from .models import Lead, Product

def get_cart_count(request: Request):
    cart = request.session.get("cart", [])
    return sum(item["qty"] for item in cart)

app = FastAPI()

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
    session_cookie="leadgen_session"
)

templates = Jinja2Templates(directory="leadgen/templates")
app.mount("/static", StaticFiles(directory="leadgen/static"), name="static")

# ---------------------------
# OPTION B — Lead Capture
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(
        "option_b.html",
        {
            "request": request,
            "cart_count": get_cart_count(request)
        }
    )

@app.post("/submit-lead")
def submit_lead(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    business_type: str = Form(""),
    service_needed: str = Form(""),
    db: Session = Depends(get_db)
):
    lead = Lead(
        name=name,
        email=email,
        phone=phone,
        business_type=business_type,
        service_needed=service_needed
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return templates.TemplateResponse(
        "lead_success.html",
        {
            "request": request,
            "lead": lead,
            "cart_count": get_cart_count(request)
        }
    )

# ---------------------------
# OPTION C — Product Catalog
# ---------------------------
@app.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "Product not found"}
        )

    related_products = (
        db.query(Product)
        .filter(Product.category == product.category, Product.id != product.id)
        .all()
    )

    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": product,
            "related_products": related_products,
            "cart_count": get_cart_count(request)
        }
    )

# ---------------------------
# ADD TO CART (with quantity)
# ---------------------------
@app.post("/add-to-cart/{product_id}")
async def add_to_cart(request: Request, product_id: int):
    form = await request.form()
    quantity = int(str(form.get("quantity", 1)))

    cart = request.session.get("cart", [])
    print("SESSION BEFORE:", request.session.get("cart"))

    # Merge duplicates
    for item in cart:
        if item["id"] == product_id:
            item["qty"] += quantity
            request.session["cart"] = cart
            print("SESSION AFTER (merged):", request.session["cart"])
            return RedirectResponse(url=f"/products/{product_id}", status_code=303)

    # Add new entry
    cart.append({"id": product_id, "qty": quantity})
    request.session["cart"] = cart
    print("SESSION AFTER (new item):", request.session["cart"])

    return RedirectResponse(url=f"/products/{product_id}", status_code=303)

@app.post("/cart/remove/{index}")
async def remove_from_cart(request: Request, index: int):
    cart = request.session.get("cart", [])

    if 0 <= index < len(cart):
        cart.pop(index)

    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)

# ---------------------------
# UPDATE QUANTITY
# ---------------------------
@app.post("/cart/update/{index}")
async def update_cart_item(request: Request, index: int):
    form = await request.form()
    qty_raw = form.get("qty")

    try:
        qty = int(qty_raw)
    except (TypeError, ValueError):
        qty = 1

    cart = request.session.get("cart", [])

    if 0 <= index < len(cart):
        cart[index]["qty"] = qty

    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)

# ---------------------------
# INCREASE QUANTITY
# ---------------------------
@app.post("/cart/increase/{index}")
async def increase_cart_quantity(request: Request, index: int):
    cart = request.session.get("cart", [])

    if 0 <= index < len(cart):
        cart[index]["qty"] += 1

    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)

# ---------------------------
# DECREASE QUANTITY
# ---------------------------
@app.post("/cart/decrease/{index}")
async def decrease_cart_quantity(request: Request, index: int):
    cart = request.session.get("cart", [])

    if 0 <= index < len(cart):
        cart[index]["qty"] -= 1

        if cart[index]["qty"] <= 0:
            cart.pop(index)

    request.session["cart"] = cart
    return RedirectResponse(url="/cart", status_code=303)

# ---------------------------
# VIEW CART (database version + recommendations)
# ---------------------------
@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    cart = request.session.get("cart", [])
    cart_items = []

    db = SessionLocal()

    # Build cart items from DB
    for index, entry in enumerate(cart):
        product = db.query(Product).filter(Product.id == entry["id"]).first()

        if product:
            raw_price = product.price or "0"
            cleaned_price = raw_price.replace("$", "").strip()

            try:
                numeric_price = float(cleaned_price)
            except ValueError:
                numeric_price = 0.0

            cart_items.append({
                "index": index,
                "id": product.id,
                "name": product.name,
                "image": product.image,
                "price": numeric_price,
                "qty": entry["qty"]
            })

    total_price = sum(item["price"] * item["qty"] for item in cart_items)
    cart_count = sum(item["qty"] for item in cart_items)

    # Recommended products from DB (with numeric prices)
    recommended_products_raw = db.query(Product).limit(3).all()
    recommended_products = []

    for p in recommended_products_raw:
        raw_price = p.price or "0"
        cleaned_price = raw_price.replace("$", "").strip()

        try:
            numeric_price = float(cleaned_price)
        except ValueError:
            numeric_price = 0.0

        recommended_products.append({
            "id": p.id,
            "name": p.name,
            "image": p.image,
            "price": numeric_price,
            "category": p.category
        })

    db.close()

    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "cart_items": cart_items,
            "total_price": total_price,
            "cart_count": cart_count,
            "recommended_products": recommended_products
        }
    )

# ---------------------------
# SUBMIT QUOTE (database version)
# ---------------------------
@app.post("/cart/submit-quote")
async def submit_cart_quote(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    cart = request.session.get("cart", [])
    print("CART SESSION CONTENTS:", cart)

    db = SessionLocal()
    products_in_cart = []

    for entry in cart:
        product = db.query(Product).filter(Product.id == entry["id"]).first()
        if product:
            products_in_cart.append(product)

    db.close()

    product_list = ", ".join([p.name for p in products_in_cart])

    print("QUOTE REQUEST:")
    print("Name:", name)
    print("Email:", email)
    print("Message:", message)
    print("Products:", product_list)

    request.session["cart"] = []  # clear cart

    return RedirectResponse(url="/products", status_code=303)

# ---------------------------
# PRODUCT CATALOG PAGE
# ---------------------------
@app.get("/products")
def product_catalog(
    request: Request,
    category: str | None = None,
    search: str | None = None
):
    db = SessionLocal()
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    products = query.all()
    db.close()

    return templates.TemplateResponse(
        "option_c.html",
        {
            "request": request,
            "products": products,
            "category": category,
            "search": search,
            "cart_count": get_cart_count(request)
        }
    )

@app.get("/debug/products")
def debug_products():
    db = SessionLocal()
    items = db.query(Product).all()
    db.close()
    return {
        "products": [
            {"id": p.id, "name": p.name, "price": p.price}
            for p in items
        ]
    }

# ---------------------------
# PRODUCT DETAIL FORM SUBMISSION
# ---------------------------
@app.post("/submit")
async def submit_form(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    product_name: str = Form(None),
    product_category: str = Form(None),
    product_id: int = Form(None)
):
    print("Lead received:")
    print("Name:", name)
    print("Email:", email)
    print("Message:", message)
    print("Product Name:", product_name)
    print("Product Category:", product_category)
    print("Product ID:", product_id)

    return templates.TemplateResponse(
        "submit_success.html",
        {
            "request": request,
            "name": name,
            "email": email,
            "message": message,
            "product_name": product_name,
            "product_category": product_category,
            "product_id": product_id
        }
    )

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "leadgen.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )
