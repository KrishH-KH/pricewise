
from decimal import Decimal

from app import create_app, db
from app.models import Plan

app = create_app()

plans = [
    {
        "name": "Starter",
        "description": "Perfect for individuals getting started.",
        "monthly_price": Decimal("299.00"),
        "yearly_price": Decimal("2990.00"),
        "features": [
            "1 user",
            "5 projects",
            "Basic analytics",
            "Email support"
        ],
        "is_popular": False
    },
    {
        "name": "Pro",
        "description": "Powerful tools for growing teams.",
        "monthly_price": Decimal("699.00"),
        "yearly_price": Decimal("6990.00"),
        "features": [
            "5 users",
            "Unlimited projects",
            "Advanced analytics",
            "Priority support"
        ],
        "is_popular": True
    },
    {
        "name": "Business",
        "description": "Advanced solutions for organizations.",
        "monthly_price": Decimal("1499.00"),
        "yearly_price": Decimal("14990.00"),
        "features": [
            "25 users",
            "Unlimited projects",
            "Advanced analytics",
            "Dedicated support"
        ],
        "is_popular": False
    }
]

with app.app_context():
    for data in plans:
        existing = db.session.execute(
            db.select(Plan).filter_by(name=data["name"])
        ).scalar_one_or_none()

        if existing:
            print(f"Already exists: {data['name']}")
            continue

        plan = Plan(**data)
        db.session.add(plan)
        print(f"Added: {data['name']}")

    db.session.commit()
    print("Database seeding completed!")
