lfs-criterion-extra
===================

Added more criterions to lfs based shop

Installation
----------------

installation is simple

    pip install lfs-criterion-extra

or

    pip install git+https://github.com/suvit/lfs-criterion-extra

After installation of the package you should add
**lfs_criterion_extra** to INSTALLED_APPS upper then **lfs** app.
This is because, this app templates overwrite lfs templates.

    INSTALLED_APPS = (
        'django.contrib.admin',
        ...
        'lfs_criterion_extra',
        ...
        'lfs',
        'lfs.core',
        ...
    )

After that you need to add tables in db

    python manage.py syncdb

That`s all.

Usage
-------------------

**lfs-criterion-extra** patches lfs criterions modules to support new criterions.
After patching you may use several new criterions:

* **OrderCountCriterion**
   checks closed order count of request.user
* **GroupCriterion**
   checks request.user is in saved group(s)
* **CategoryCriterion**
   checks product or products in cart are in saved categories
* **ProductCriterion**
   checks product or products in cart are in saved list of products
* **OrderCompositionCriterion**
   checks that in cart 
* **DiscountCriterion**
   checks that saved discounts are valid or unvalid
* **OrderSummCriterion**
   checks closed order summ of prices
* **ManufacturerCriterion**
   checks product`s manufacturer is in saved list of manufacturers
* **TimeCriterion**
   checks now time to compare with saved time
* **CartAmountCriterion**
   checks cart amount
* **MaxWeightCriterion**
   chacks max weight of the products in cart
* **ForSaleCriterion**
   checks product or products in cart are for_sale
* **ManualDeliveryTimeCriterion**
   checks product or products in cart are with manual delivery time
* **FullUserCriterion** (AdvancedUserCriterion)
   added ability to check that user is anonymous or not.
* **ProfitCriterion** (not worked with base lfs, needed prices from supplier)
   checks product profit

You may choose new criterions from criterion`s tab
of delivery method, payment methods and discounts.

Added own criterions
------------------------------

You may inherit **Criterion** or **NumberCriterion**

    from lfs_criterion_extra.models import Criterion, NumberCriterion

    class FooCriterion(NumberCriterion):

        foo = models.IntegerField("Foo"), default=0)

        'may be other model fields'

        value_attr = 'foo'  # from that attribute get value to compare
        content_type = 'foo'  # internal id of the criterion
        name = 'Foo'  # displayable value

        def is_valid(self, request, product=None):
            how_many_foo = product.name.count('foo')
            return self.test_value(how_many_foo)

that`s all, your criterion is appeared in the criterion list.

TODO
------

* move monkey.py to lfs.criterion.core (merge or move to lfs 0.8)
* write tests
