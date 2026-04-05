"""User management routes."""
import csv
import io
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models.user import User
from app.errors import NotFoundError, ValidationError
from app.logging_config import get_logger

users_bp = Blueprint("users", __name__, url_prefix="/users")
logger = get_logger("users")


@users_bp.route("", methods=["GET"])
def list_users():
    """List all users with optional pagination."""
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int, default=20)

    query = User.select().order_by(User.id)

    if page is not None:
        # Pagination requested
        query = query.paginate(page, per_page)

    users = [user.to_dict() for user in query]
    return jsonify(users), 200


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    """Get a user by ID."""
    user = User.select().where(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")
    return jsonify(user.to_dict()), 200


@users_bp.route("", methods=["POST"])
def create_user():
    """Create a new user."""
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    email = data.get("email")

    if not username or not isinstance(username, str):
        raise ValidationError("username is required and must be a string")
    if not email or not isinstance(email, str):
        raise ValidationError("email is required and must be a string")

    # Check for duplicates
    existing = User.select().where(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        raise ValidationError("Username or email already exists")

    user = User.create(
        username=username.strip(),
        email=email.strip(),
    )

    logger.info("User created", extra={"component": "users", "user_id": user.id})
    return jsonify(user.to_dict()), 201


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id: int):
    """Update a user."""
    user = User.select().where(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")

    data = request.get_json(silent=True) or {}

    if "username" in data:
        if not isinstance(data["username"], str):
            raise ValidationError("username must be a string")
        user.username = data["username"].strip()
    if "email" in data:
        if not isinstance(data["email"], str):
            raise ValidationError("email must be a string")
        user.email = data["email"].strip()

    user.save()

    logger.info("User updated", extra={"component": "users", "user_id": user.id})
    return jsonify(user.to_dict()), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    """Delete a user."""
    user = User.select().where(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found")

    user.delete_instance()

    logger.info("User deleted", extra={"component": "users", "user_id": user_id})
    return jsonify({"message": "User deleted"}), 200


@users_bp.route("/bulk", methods=["POST"])
def bulk_load_users():
    """Bulk load users from CSV file."""
    if "file" not in request.files:
        raise ValidationError("No file provided")

    file = request.files["file"]
    if not file.filename:
        raise ValidationError("No file selected")

    # Read CSV content
    try:
        content = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        imported_count = 0
        for row in reader:
            # Parse the CSV row
            user_id = row.get("id")
            username = row.get("username")
            email = row.get("email")
            created_at = row.get("created_at")

            if not username or not email:
                continue

            # Parse created_at if provided
            parsed_created_at = None
            if created_at:
                try:
                    parsed_created_at = datetime.fromisoformat(created_at.replace(" ", "T"))
                except ValueError:
                    parsed_created_at = None

            # Check if user already exists (by id or username or email)
            existing = None
            if user_id:
                existing = User.select().where(User.id == int(user_id)).first()

            if existing:
                # Update existing user
                existing.username = username.strip()
                existing.email = email.strip()
                if parsed_created_at:
                    existing.created_at = parsed_created_at
                existing.save()
            else:
                # Create new user, potentially with specific ID
                user_data = {
                    "username": username.strip(),
                    "email": email.strip(),
                }
                if parsed_created_at:
                    user_data["created_at"] = parsed_created_at

                if user_id:
                    user_data["id"] = int(user_id)

                User.insert(user_data).on_conflict(
                    conflict_target=[User.id],
                    preserve=[User.username, User.email, User.created_at]
                ).execute()

            imported_count += 1

        logger.info("Bulk users imported", extra={
            "component": "users",
            "count": imported_count
        })

        return jsonify({"count": imported_count, "imported": imported_count}), 201

    except Exception as e:
        logger.error("Bulk import failed", extra={
            "component": "users",
            "error": str(e)
        })
        raise ValidationError(f"Failed to parse CSV: {str(e)}")
