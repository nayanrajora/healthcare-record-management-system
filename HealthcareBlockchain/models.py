"""
models.py
=========
Domain Models and Data Transfer Objects (DTOs) for the Healthcare Record Management System.

These clean Python representations wrap SQLite rows to provide safe, explicit,
and typed access across Flask routes and services.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    role: str
    full_name: str
    email: str
    is_active: bool
    created_at: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            full_name=row["full_name"],
            email=row["email"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"]
        )


@dataclass
class Patient:
    id: int
    user_id: int
    patient_code: str
    full_name: str
    date_of_birth: str
    gender: str
    blood_group: str
    contact_phone: str
    address: str
    emergency_contact: str
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Patient":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            patient_code=row["patient_code"],
            full_name=row["full_name"] if "full_name" in row.keys() else "",
            date_of_birth=row["date_of_birth"],
            gender=row["gender"],
            blood_group=row["blood_group"],
            contact_phone=row["contact_phone"],
            address=row["address"],
            emergency_contact=row["emergency_contact"],
            created_at=row["created_at"]
        )


@dataclass
class Doctor:
    id: int
    user_id: int
    doctor_code: str
    full_name: str
    specialization: str
    license_number: str
    contact_phone: str
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Doctor":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            doctor_code=row["doctor_code"],
            full_name=row["full_name"] if "full_name" in row.keys() else "",
            specialization=row["specialization"],
            license_number=row["license_number"],
            contact_phone=row["contact_phone"],
            created_at=row["created_at"]
        )


@dataclass
class MedicalRecord:
    id: int
    patient_id: int
    doctor_id: int
    record_type: str
    diagnosis: str
    prescription: str
    current_version: int
    created_at: str
    updated_at: str
    patient_name: Optional[str] = None
    patient_code: Optional[str] = None
    doctor_name: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "MedicalRecord":
        keys = row.keys()
        return cls(
            id=row["id"],
            patient_id=row["patient_id"],
            doctor_id=row["doctor_id"],
            record_type=row["record_type"],
            diagnosis=row["diagnosis"],
            prescription=row["prescription"],
            current_version=row["current_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            patient_name=row["patient_name"] if "patient_name" in keys else None,
            patient_code=row["patient_code"] if "patient_code" in keys else None,
            doctor_name=row["doctor_name"] if "doctor_name" in keys else None
        )


@dataclass
class BlockchainBlock:
    id: int
    block_index: int
    timestamp: str
    event_type: str
    record_id: Optional[int]
    record_version: Optional[int]
    record_hash: str
    previous_hash: str
    block_hash: str

    @classmethod
    def from_row(cls, row) -> "BlockchainBlock":
        return cls(
            id=row["id"],
            block_index=row["block_index"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            record_id=row["record_id"],
            record_version=row["record_version"],
            record_hash=row["record_hash"],
            previous_hash=row["previous_hash"],
            block_hash=row["block_hash"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "block_index": self.block_index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "record_id": self.record_id,
            "record_version": self.record_version,
            "record_hash": self.record_hash,
            "previous_hash": self.previous_hash,
            "block_hash": self.block_hash
        }
