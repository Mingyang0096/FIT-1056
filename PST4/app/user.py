import re

class User:
    """
    Base class for system users with strict name validation.
    Ensures names contain only letters and spaces.
    Supports safe updates and JSON-friendly serialization.
    Accepts flexible ID keys when loading from dict.
    """

    # Precompiled regex: only letters (A–Z, a–z) and spaces allowed
    _NAME_PATTERN = re.compile(r'^[A-Za-z\s]+$')

    def __init__(self, user_id, name):
        # Normalize and check non-empty
        name_str = (name or "").strip()
        if not name_str:
            raise ValueError("Name cannot be empty.")
        # Full match ensures no invalid characters
        if not self._NAME_PATTERN.fullmatch(name_str):
            raise ValueError("Name must contain only letters and spaces.")
        
        self.id = user_id
        self.name = name_str

    def update_name(self, new_name):
        """Update name with same validation rules as init."""
        name_str = (new_name or "").strip()
        if not name_str:
            raise ValueError("Name cannot be empty.")
        if not self._NAME_PATTERN.fullmatch(name_str):
            raise ValueError("Name must contain only letters and spaces.")
        self.name = name_str

    def to_dict(self):
        """Return dict with consistent external key names."""
        return {
            "user_id": self.id,
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data):
        """Create instance from dict, accepting 'user_id' or 'id'."""
        if not isinstance(data, dict):
            raise TypeError("Expected a dict to construct a User.")
        user_id = data.get("user_id", data.get("id"))
        name    = data.get("name")
        return cls(user_id=user_id, name=name)
