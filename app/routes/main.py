
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import secrets
import hmac

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from flask_login import login_required, current_user

from app import db
from app.models import Plan, Subscription, Coupon, Transaction

main_bp = Blueprint("main", __name__)


def add_months(date_value, months):
    """Add calendar months without requiring another package."""
    import calendar

    month_index = date_value.month - 1 + months
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])

    return date_value.replace(year=year, month=month, day=day)


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/pricing")
def pricing():
    return render_template("pricing.html")


@main_bp.route("/compare")
def compare():
    return render_template("compare.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/checkout/<int:plan_id>", methods=["GET", "POST"])
@login_required
def checkout(plan_id):

    plan = db.session.get(Plan, plan_id)

    if plan is None or not plan.is_active:
        flash("This pricing plan is no longer available.", "error")
        return redirect(url_for("main.pricing"))

    if request.method == "GET":
        billing_cycle = request.args.get("cycle", "monthly").lower()

        if billing_cycle not in ("monthly", "yearly"):
            billing_cycle = "monthly"

        csrf_token = secrets.token_urlsafe(32)
        session["checkout_csrf_token"] = csrf_token

        amount = (
            Decimal(str(plan.yearly_price))
            if billing_cycle == "yearly"
            else Decimal(str(plan.monthly_price))
        )

        return render_template(
            "checkout.html",
            plan=plan,
            billing_cycle=billing_cycle,
            amount=amount,
            csrf_token=csrf_token
        )

    # Validate checkout form token
    submitted_token = request.form.get("csrf_token", "")
    stored_token = session.get("checkout_csrf_token", "")

    if (
        not stored_token
        or not submitted_token
        or not hmac.compare_digest(submitted_token, stored_token)
    ):
        flash("Your checkout session expired. Please try again.", "error")
        return redirect(url_for("main.checkout", plan_id=plan.id))

    billing_cycle = request.form.get("billing_cycle", "").lower()
    coupon_code = request.form.get("coupon_code", "").strip().upper()
    payment_method = request.form.get("payment_method", "")

    if billing_cycle not in ("monthly", "yearly"):
        flash("Invalid billing cycle.", "error")
        return redirect(url_for("main.checkout", plan_id=plan.id))

    allowed_methods = ("demo", "upi_demo", "card_demo")

    if payment_method not in allowed_methods:
        flash("Invalid demo payment method.", "error")
        return redirect(url_for("main.checkout", plan_id=plan.id))

    amount = (
        Decimal(str(plan.yearly_price))
        if billing_cycle == "yearly"
        else Decimal(str(plan.monthly_price))
    )

    coupon = None

    if coupon_code:
        coupon = db.session.execute(
            db.select(Coupon).filter_by(code=coupon_code)
        ).scalar_one_or_none()

        if coupon is None or not coupon.is_active:
            flash("Invalid or inactive coupon code.", "error")
            return redirect(url_for("main.checkout", plan_id=plan.id))

        now = datetime.now(timezone.utc)

        if coupon.expires_at:
            expiry = coupon.expires_at

            if expiry.tzinfo is None:
                now = now.replace(tzinfo=None)

            if expiry <= now:
                flash("This coupon has expired.", "error")
                return redirect(url_for("main.checkout", plan_id=plan.id))

        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            flash("This coupon has reached its usage limit.", "error")
            return redirect(url_for("main.checkout", plan_id=plan.id))

        discount_type = coupon.discount_type.lower()
        discount_value = Decimal(str(coupon.discount_value))

        if discount_type in ("percentage", "percent"):
            if discount_value <= 0 or discount_value > 100:
                flash("This coupon has an invalid discount.", "error")
                return redirect(url_for("main.checkout", plan_id=plan.id))

            discount = amount * discount_value / Decimal("100")

        elif discount_type in ("fixed", "flat"):
            if discount_value <= 0:
                flash("This coupon has an invalid discount.", "error")
                return redirect(url_for("main.checkout", plan_id=plan.id))

            discount = min(discount_value, amount)

        else:
            flash("Unsupported coupon discount type.", "error")
            return redirect(url_for("main.checkout", plan_id=plan.id))

        amount = max(Decimal("0.00"), amount - discount)

    # Create the simulated subscription and transaction together.
    now = datetime.now(timezone.utc)
    duration_months = 12 if billing_cycle == "yearly" else 1
    end_date = add_months(now, duration_months)

    try:
        # Cancel any previous active subscription for this customer.
        previous_subscriptions = db.session.execute(
            db.select(Subscription).filter_by(
                user_id=current_user.id,
                status="active"
            )
        ).scalars().all()

        for previous in previous_subscriptions:
            previous.status = "cancelled"

        subscription = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            billing_cycle=billing_cycle,
            status="active",
            start_date=now,
            end_date=end_date
        )

        db.session.add(subscription)
        db.session.flush()

        transaction = Transaction(
            user_id=current_user.id,
            subscription_id=subscription.id,
            amount=amount,
            payment_method=payment_method,
            status="successful",
            reference="PW-" + secrets.token_hex(8).upper()
        )

        db.session.add(transaction)

        if coupon:
            coupon.used_count += 1

        db.session.commit()
        session.pop("checkout_csrf_token", None)

        flash(
            "Demo payment successful! Your subscription is now active.",
            "success"
        )

        return redirect(url_for("main.dashboard"))

    except Exception:
        db.session.rollback()
        flash("Checkout could not be completed. Please try again.", "error")
        return redirect(url_for("main.checkout", plan_id=plan.id))
