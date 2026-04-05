"""User management routes."""
import csv
import io
from datetime import datetime

from flask import Blueprint, jsonify, request
from peewee import fn

from app.models.user import User
from app.errors import NotFoundError, ValidationError
from app.logging_config import get_logger

users_bp = Blueprint("users", __name__, url_prefix="/users")
logger = get_logger("users")


def validate_json_body():
    """Validate that request has proper JSON body (Fractured Vessel)."""
    content_type = request.content_type or ""
    if request.method in ("POST", "PUT") and request.data:
        if "application/json" not in content_type:
            raise ValidationError("Content-Type must be application/json")
        try:
            data = request.get_json(force=True)
            if data is None:
                raise ValidationError("Request body must be valid JSON")
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            return data
        except Exception as e:
            if "ValidationError" in str(type(e)):
                raise
            raise ValidationError("Request body must be valid JSON")
    return request.get_json(silent=True) or {}


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
    data = validate_json_body()

    username = data.get("username")
    email = data.get("email")

    # Validate types (Deceitful Scroll - reject wrong types)
    if not username or not isinstance(username, str):
        raise ValidationError("username is required and must be a string")
    if not email or not isinstance(email, str):
        raise ValidationError("email is required and must be a string")

    # Check for duplicates (Twin's Paradox)
    existing = User.select().where(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        raise ValidationError("Username or email already exists")

    # Reset sequence to avoid ID conflicts after bulk imports
    # Get the max ID and ensure sequence is past it
    max_id = User.select(fn.MAX(User.id)).scalar() or 0

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

    data = validate_json_body()

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
        skipped_count = 0
        for row in reader:
            # Parse the CSV row
            user_id = row.get("id")
            username = row.get("username")
            email = row.get("email")
            created_at = row.get("created_at")

            if not username or not email:
                skipped_count += 1
                continue

            # Parse created_at if provided
            parsed_created_at = None
            if created_at:
                try:
                    parsed_created_at = datetime.fromisoformat(created_at.replace(" ", "T"))
                except ValueError:
                    parsed_created_at = None

            # Check if user already exists by ID, username, or email
            existing_by_id = None
            existing_by_unique = None

            if user_id:
                existing_by_id = User.select().where(User.id == int(user_id)).first()

            # Check for username/email conflicts with OTHER users
            existing_by_unique = User.select().where(
                (User.username == username.strip()) | (User.email == email.strip())
            ).first()

            if existing_by_id:
                # Update existing user by ID
                existing_by_id.username = username.strip()
                existing_by_id.email = email.strip()
                if parsed_created_at:
                    existing_by_id.created_at = parsed_created_at
                existing_by_id.save()
                imported_count += 1
            elif existing_by_unique:
                # User exists with same username/email - update them
                existing_by_unique.username = username.strip()
                existing_by_unique.email = email.strip()
                if parsed_created_at:
                    existing_by_unique.created_at = parsed_created_at
                existing_by_unique.save()
                imported_count += 1
            else:
                # Create new user
                user_data = {
                    "username": username.strip(),
                    "email": email.strip(),
                }
                if parsed_created_at:
                    user_data["created_at"] = parsed_created_at

                if user_id:
                    user_data["id"] = int(user_id)

                User.insert(user_data).execute()
                imported_count += 1

        # Reset the sequence to avoid ID conflicts after bulk import
        from app.database import db
        max_id = User.select(fn.MAX(User.id)).scalar() or 0
        if max_id > 0:
            db.execute_sql(f"SELECT setval('users_id_seq', {max_id}, true)")

        logger.info("Bulk users imported", extra={
            "component": "users",
            "count": imported_count,
            "skipped": skipped_count
        })

        return jsonify({"count": imported_count, "imported": imported_count}), 201

    except Exception as e:
        logger.error("Bulk import failed", extra={
            "component": "users",
            "error": str(e)
        })
        raise ValidationError(f"Failed to parse CSV: {str(e)}")
