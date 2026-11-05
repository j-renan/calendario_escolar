from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    id: Optional[int]
    name: str
    email: str
    password_hash: str
    role: str = "coordenador"
    is_active: bool = True
    created_at: Optional[datetime] = None

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data
