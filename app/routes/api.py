
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Plan, Subscription, Transaction

api_bp = Blueprint("api", __name__)


def serialize_plan(plan):
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "monthly_price": float(plan.monthly_price),
        "yearly_price": float(plan.yearly_price),
        "features": plan.features,
        "is_popular": plan.is_popular,
        "is_active": plan.is_active
    }


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "success",
        "application": "PRICEWISE",
        "message": "API is running",
        "version": "1.0.0"
    })


@api_bp.route("/plans", methods=["GET"])
def get_plans():
    plans = db.session.execute(
        db.select(Plan)
        .filter_by(is_active=True)
        .order_by(Plan.monthly_price)
    ).scalars().all()

    return jsonify({
        "success": True,
        "count": len(plans),
        "plans": [serialize_plan(plan) for plan in plans]
    })


@api_bp.route("/plans/<int:plan_id>", methods=["GET"])
def get_plan(plan_id):
    plan = db.session.get(Plan, plan_id)

    if plan is None or not plan.is_active:
        return jsonify({
            "success": False,
            "message": "Plan not found"
        }), 404

    return jsonify({
        "success": True,
        "plan": serialize_plan(plan)
    })


# CUSTOMER DASHBOARD API
@api_bp.route("/me/dashboard", methods=["GET"])
@login_required
def customer_dashboard():

    # Find the customer's latest active subscription
    subscription = db.session.execute(
        db.select(Subscription)
        .filter_by(
            user_id=current_user.id,
            status="active"
        )
        .order_by(Subscription.start_date.desc())
    ).scalars().first()

    subscription_data = None

    if subscription:
        subscription_data = {
            "id": subscription.id,
            "status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "start_date": (
                subscription.start_date.isoformat()
                if subscription.start_date else None
            ),
            "end_date": (
                subscription.end_date.isoformat()
                if subscription.end_date else None
            ),
            "plan": serialize_plan(subscription.plan)
        }

    # Get the latest 10 transactions belonging to this customer
    transactions = db.session.execute(
        db.select(Transaction)
        .filter_by(user_id=current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(10)
    ).scalars().all()

    transaction_data = [
        {
            "id": transaction.id,
            "reference": transaction.reference,
            "amount": float(transaction.amount),
            "payment_method": transaction.payment_method,
            "status": transaction.status,
            "created_at": (
                transaction.created_at.isoformat()
                if transaction.created_at else None
            )
        }
        for transaction in transactions
    ]

    return jsonify({
        "success": True,
        "customer": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email
        },
        "subscription": subscription_data,
        "transactions": transaction_data
    })
