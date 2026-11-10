
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Please complete all required fields.", "error")
            return render_template("register.html")

        if len(name) > 100 or len(email) > 150:
            flash("Name or email is too long.", "error")
            return render_template("register.html")

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        existing_user = User.query.filter(
            func.lower(User.email) == email
        ).first()

        if existing_user:
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            role="customer"
        )

        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            login_user(user)

            flash("Your PRICEWISE account was created successfully!", "success")
            return redirect(url_for("main.dashboard"))

        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Please enter your email and password.", "error")
            return render_template("login.html")

        user = User.query.filter(
            func.lower(User.email) == email
        ).first()

        if user and user.check_password(password):

            login_user(user, remember=remember)

            flash("Welcome back to PRICEWISE!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():

    logout_user()
    flash("You have been logged out.", "success")

    return redirect(url_for("main.home"))
