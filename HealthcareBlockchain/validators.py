"""
validators.py
=============
Input Validation and Data Sanitization Utilities.

Enforces server-side constraints on medical records, user accounts, and authentication payloads.
Hiding buttons or relying on client-side JS validation is never sufficient for security.
"""

import re
from typing import Tuple, Optional

# Constants for allowed values
VALID_ROLES = {"admin", "doctor", "patient"}
VALID_RECORD_TYPES = {"Consultation", "Diagnosis", "Prescription", "Lab Result"}
VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Validates that a username is alphanumeric (with underscores) between 3 and 30 chars."""
    if not username or not isinstance(username, str):
        return False, "Username is required."
    clean = username.strip()
    if not USERNAME_REGEX.match(clean):
        return False, "Username must be 3-30 characters long and contain only letters, numbers, and underscores."
    return True, None


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validates password strength.
    Requires at least 8 characters, at least one letter, and at least one digit or special char.
    """
    if not password or not isinstance(password, str):
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one number or special character."
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validates email format."""
    if not email or not isinstance(email, str):
        return False, "Email address is required."
    clean = email.strip()
    if not EMAIL_REGEX.match(clean) or len(clean) > 100:
        return False, "Please enter a valid email address."
    return True, None


def validate_medical_record_input(
    record_type: str,
    diagnosis: str,
    prescription: str
) -> Tuple[bool, Optional[str]]:
    """
    Validates medical record clinical notes and prescriptions.
    Enforces non-empty values, valid record types, and reasonable character lengths.
    """
    if not record_type or record_type.strip() not in VALID_RECORD_TYPES:
        return False, f"Invalid record type. Must be one of: {', '.join(sorted(VALID_RECORD_TYPES))}."
    
    if not diagnosis or not diagnosis.strip():
        return False, "Diagnosis / Clinical Notes cannot be empty."
    if len(diagnosis.strip()) < 5:
        return False, "Diagnosis / Clinical Notes must be at least 5 characters long."
    if len(diagnosis.strip()) > 5000:
        return False, "Diagnosis notes exceed maximum permitted length (5000 characters)."

    if not prescription or not prescription.strip():
        return False, "Prescription / Treatment details cannot be empty."
    if len(prescription.strip()) < 5:
        return False, "Prescription / Treatment must be at least 5 characters long."
    if len(prescription.strip()) > 5000:
        return False, "Prescription details exceed maximum permitted length (5000 characters)."

    return True, None
