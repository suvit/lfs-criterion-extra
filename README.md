lfs-criterion-extra
===================

Added more criterions to lfs based shop

Installation
----------------

installation is simple

    pip install lfs-criterion-extra

or

    pip install git+https://github.com/suvit/lfs-criterion-extra

After instalation of the package you should add
**lfs_criterion_extra** to INSTALLED_APPS before **lfs** app.
This is because, this app overwrite lfs templates.

Usage
-------------------

**lfs-criterion-extra** patch lfs criterions modules to support new criterions.
After patching you may use several new criterions:

* **OrderCountCriterion**
   checks closed order count of request.user
* **GroupCriterion**
   checks request.user is in saved group(s)
* **CategoryCriterion**
   checks product is in saved categories
* **ProductCriterion**
   checks product is in saved list of products
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

TODO
====
list criterions in sorted order
move monkey.py to lfs.core (merge or move to lfs 0.8)
write tests
