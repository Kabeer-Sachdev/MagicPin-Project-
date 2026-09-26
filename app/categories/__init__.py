from __future__ import annotations

from typing import Dict, Type
from app.categories.dentist import DentistCategoryStrategy
from app.categories.salon import SalonCategoryStrategy
from app.categories.restaurant import RestaurantCategoryStrategy
from app.categories.gym import GymCategoryStrategy
from app.categories.pharmacy import PharmacyCategoryStrategy

STRATEGIES: Dict[str, Any] = {
    "dentists": DentistCategoryStrategy,
    "salons": SalonCategoryStrategy,
    "restaurants": RestaurantCategoryStrategy,
    "gyms": GymCategoryStrategy,
    "pharmacies": PharmacyCategoryStrategy,
}


def get_category_strategy(category_slug: str):
    return STRATEGIES.get(category_slug, DentistCategoryStrategy)
