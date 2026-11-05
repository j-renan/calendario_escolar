from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from models.user import User
from models.calendar import SchoolCalendar

class IUserRepository(ABC):
    """Interface Segregation Principle: User persistence contract."""
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def list_all(self) -> List[User]:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        pass

class ICalendarRepository(ABC):
    """Interface Segregation Principle: Calendar persistence contract."""
    @abstractmethod
    def get_by_id(self, calendar_id: int) -> Optional[SchoolCalendar]:
        pass

    @abstractmethod
    def get_latest(self) -> Optional[SchoolCalendar]:
        pass

    @abstractmethod
    def get_by_period(self, semester_year: str) -> Optional[SchoolCalendar]:
        pass

    @abstractmethod
    def create(self, calendar: SchoolCalendar) -> SchoolCalendar:
        pass

    @abstractmethod
    def update(self, calendar: SchoolCalendar) -> SchoolCalendar:
        pass

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, calendar_id: int) -> bool:
        pass

    @abstractmethod
    def add_history(self, calendar_id: int, action: str, snapshot: dict, user_id: Optional[int]) -> int:
        pass

    @abstractmethod
    def get_history(self, calendar_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        pass

class ICategoryRepository(ABC):
    @abstractmethod
    def list_all(self, active_only: bool = False) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create(self, code: str, name: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update(self, category_id: int, name: str, is_active: bool) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, category_id: int) -> bool:
        pass
