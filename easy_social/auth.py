from __future__ import annotations

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .captcha import (
    CAPTCHA_SESSION_KEY,
    CAPTCHA_TEST_SESSION_KEY,
    captcha_digest,
    captcha_matches,
    generate_captcha_code,
    render_captcha_svg,
)
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _refresh_captcha() -> str:
    code = generate_captcha_code()
    session[CAPTCHA_SESSION_KEY] = captcha_digest(code, current_app.config["SECRET_KEY"])
    if current_app.config["CAPTCHA_TESTING_SHOW_ANSWER"]:
        session[CAPTCHA_TEST_SESSION_KEY] = code
    return code


def _captcha_answer() -> str:
    if current_app.config["CAPTCHA_TESTING_SHOW_ANSWER"]:
        return session.get(CAPTCHA_TEST_SESSION_KEY) or _refresh_captcha()
    return _refresh_captcha()


@bp.get("/captcha.svg")
def captcha_image():
    response = Response(render_captcha_svg(_captcha_answer()), mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    captcha_code = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        expected_captcha_digest = session.pop(CAPTCHA_SESSION_KEY, None)
        session.pop(CAPTCHA_TEST_SESSION_KEY, None)
        captcha_response = request.form.get("captcha", "")

        error = None
        if not captcha_matches(
            expected_captcha_digest,
            captcha_response,
            current_app.config["SECRET_KEY"],
        ):
            error = "CAPTCHA verification failed. Please try again."
        elif not username or not email or not password:
            error = "Username, email, and password are required."
        elif len(username) > 40:
            error = "Username must be 40 characters or fewer."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif User.query.filter_by(email=email).first():
            error = "That email is already registered."

        if error:
            flash(error, "error")
            captcha_code = _refresh_captcha()
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("social.feed"))
    else:
        captcha_code = _captcha_answer()

    return render_template(
        "auth/register.html",
        captcha_test_answer=captcha_code
        if current_app.config["CAPTCHA_TESTING_SHOW_ANSWER"]
        else None,
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == username_or_email)
            | (User.email == username_or_email.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("social.feed"))

        flash("Invalid username/email or password.", "error")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
