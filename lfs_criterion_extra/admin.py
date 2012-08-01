
from django.contrib import admin
from django.db.models.base import ModelBase

from lfs_criterion_extra.models import (OrderCountCriterion,
                                        GroupCriterion,
                                        CategoryCriterion,
                                        ProductCriterion,
                                        OrderCompositionCriterion,
                                        CompositionCategory,
                                        DiscountCriterion,
                                        OrderSummCriterion,
                                        ManufacturerCriterion,
                                        TimeCriterion,
                                        CartAmountCriterion,
                                        MaxWeightCriterion,
                                        ForSaleCriterion,
                                        FullUserCriterion,
                                        ProfitCriterion)

for item in vars().values():
    if isinstance(item, ModelBase):
        admin.site.register(item)
