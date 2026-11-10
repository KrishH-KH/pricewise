
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import User, Plan, Subscription, Transaction

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_plans = Plan.query.filter_by(is_active=True).count()
    total_subscriptions = Subscription.query.filter_by(status="active").count()

    total_revenue = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter_by(status="successful")
        .scalar()
    )

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_plans=total_plans,
        total_subscriptions=total_subscriptions,
        total_revenue=total_revenue,
    )


@admin_bp.route("/plans", methods=["GET", "POST"])
@login_required
@admin_required
def plans():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        monthly_price_text = request.form.get("monthly_price", "").strip()
        yearly_price_text = request.form.get("yearly_price", "").strip()
        features_text = request.form.get("features", "").strip()
        is_popular = request.form.get("is_popular") == "on"

        if not all([name, description, monthly_price_text, yearly_price_text, features_text]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("admin.plans"))

        if len(name) > 100:
            flash("Plan name must be 100 characters or fewer.", "error")
            return redirect(url_for("admin.plans"))

        existing_plan = Plan.query.filter(
            func.lower(Plan.name) == name.lower()
        ).first()

        if existing_plan:
            flash("A plan with that name already exists.", "error")
            return redirect(url_for("admin.plans"))

        try:
            monthly_price = Decimal(monthly_price_text)
            yearly_price = Decimal(yearly_price_text)

            if not monthly_price.is_finite() or not yearly_price.is_finite():
                raise InvalidOperation

            if monthly_price < 0 or yearly_price < 0:
                flash("Prices cannot be negative.", "error")
                return redirect(url_for("admin.plans"))

        except (InvalidOperation, ValueError):
            flash("Enter valid monthly and yearly prices.", "error")
            return redirect(url_for("admin.plans"))

        features = [
            feature.strip()
            for feature in features_text.splitlines()
            if feature.strip()
        ]

        if not features:
            flash("Add at least one plan feature.", "error")
            return redirect(url_for("admin.plans"))

        try:
            if is_popular:
                Plan.query.update({Plan.is_popular: False})

            new_plan = Plan(
                name=name,
                description=description,
                monthly_price=monthly_price,
                yearly_price=yearly_price,
                features=features,
                is_popular=is_popular,
                is_active=True,
            )

            db.session.add(new_plan)
            db.session.commit()

            flash(f"{name} plan was created successfully.", "success")

        except Exception:
            db.session.rollback()
            flash("Something went wrong while creating the plan.", "error")

        return redirect(url_for("admin.plans"))

    all_plans = Plan.query.order_by(Plan.created_at.desc()).all()

    return render_template("admin/plans.html", plans=all_plans)


@admin_bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_plan(plan_id):
    plan = db.get_or_404(Plan, plan_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        monthly_text = request.form.get("monthly_price", "").strip()
        yearly_text = request.form.get("yearly_price", "").strip()
        features_text = request.form.get("features", "").strip()
        is_popular = request.form.get("is_popular") == "on"

        if not all([name, description, monthly_text, yearly_text, features_text]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("admin.edit_plan", plan_id=plan.id))

        duplicate = Plan.query.filter(
            func.lower(Plan.name) == name.lower(),
            Plan.id != plan.id
        ).first()

        if duplicate:
            flash("Another plan already uses that name.", "error")
            return redirect(url_for("admin.edit_plan", plan_id=plan.id))

        try:
            monthly_price = Decimal(monthly_text)
            yearly_price = Decimal(yearly_text)

            if (
                not monthly_price.is_finite()
                or not yearly_price.is_finite()
                or monthly_price < 0
                or yearly_price < 0
            ):
                raise InvalidOperation

        except (InvalidOperation, ValueError):
            flash("Enter valid non-negative prices.", "error")
            return redirect(url_for("admin.edit_plan", plan_id=plan.id))

        features = [
            item.strip()
            for item in features_text.splitlines()
            if item.strip()
        ]

        if not features:
            flash("Add at least one feature.", "error")
            return redirect(url_for("admin.edit_plan", plan_id=plan.id))

        try:
            if is_popular:
                Plan.query.filter(Plan.id != plan.id).update(
                    {Plan.is_popular: False}
                )

            plan.name = name
            plan.description = description
            plan.monthly_price = monthly_price
            plan.yearly_price = yearly_price
            plan.features = features
            plan.is_popular = is_popular

            db.session.commit()
            flash("Plan updated successfully.", "success")
            return redirect(url_for("admin.plans"))

        except Exception:
            db.session.rollback()
            flash("Could not update the plan. Please try again.", "error")

    return render_template("admin/edit_plan.html", plan=plan)


@admin_bp.route("/plans/<int:plan_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_plan(plan_id):
    plan = db.get_or_404(Plan, plan_id)

    try:
        plan.is_active = not plan.is_active
        db.session.commit()

        state = "activated" if plan.is_active else "deactivated"
        flash(f"{plan.name} has been {state}.", "success")

    except Exception:
        db.session.rollback()
        flash("Could not update the plan status.", "error")

    return redirect(url_for("admin.plans"))

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin/users.html",
        users=all_users
    )


@admin_bp.route("/transactions")
@login_required
@admin_required
def transactions():
    all_transactions = Transaction.query.order_by(
        Transaction.created_at.desc()
    ).all()

    return render_template(
        "admin/transactions.html",
        transactions=all_transactions
    )
