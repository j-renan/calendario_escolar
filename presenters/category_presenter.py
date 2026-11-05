import re
import unicodedata
from uuid import uuid4

from core.exceptions import NotFoundError, ValidationError
from models.repositories.base import ICategoryRepository


class CategoryPresenter:
    def __init__(self, category_repo: ICategoryRepository):
        self.category_repo = category_repo

    def list_categories(self, active_only: bool = False):
        return self.category_repo.list_all(active_only=active_only)

    def create(self, name: str) -> dict:
        name = name.strip() if isinstance(name, str) else ""
        if not name or len(name) > 120:
            raise ValidationError("Informe um nome de categoria com até 120 caracteres.")
        if any(item["name"].casefold() == name.casefold() for item in self.category_repo.list_all()):
            raise ValidationError("Já existe uma categoria com este nome.")

        normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
        slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "categoria"
        return self.category_repo.create(f"{slug}-{uuid4().hex[:8]}", name)

    def update(self, category_id: int, name: str, is_active: bool) -> dict:
        name = name.strip() if isinstance(name, str) else ""
        if not name or len(name) > 120:
            raise ValidationError("Informe um nome de categoria com até 120 caracteres.")
        current = self.category_repo.get_by_id(category_id)
        if not current:
            raise NotFoundError("Categoria não encontrada.")
        for item in self.category_repo.list_all():
            if item["id"] != category_id and item["name"].casefold() == name.casefold():
                raise ValidationError("Já existe uma categoria com este nome.")
        updated = self.category_repo.update(category_id, name, is_active)
        if not updated:
            raise NotFoundError("Categoria não encontrada.")
        return updated

    def delete(self, category_id: int) -> None:
        if not self.category_repo.get_by_id(category_id):
            raise NotFoundError("Categoria não encontrada.")
        if not self.category_repo.delete(category_id):
            raise NotFoundError("Categoria não encontrada.")
