# -*- coding: utf-8 -*-
# monkeypatch lfs functions
import monkey

import time
import datetime
from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes import generic
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Sum
from django.forms.formsets import formset_factory
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

from lfs.catalog.models import Category, Product
from lfs.cart.utils import get_cart
from lfs.criteria.models.criteria_objects import CriteriaObjects
from lfs.criteria.settings import EQUAL
from lfs.criteria.settings import LESS_THAN
from lfs.criteria.settings import LESS_THAN_EQUAL
from lfs.criteria.settings import GREATER_THAN
from lfs.criteria.settings import GREATER_THAN_EQUAL
from lfs.criteria.settings import SELECT_OPERATORS
from lfs.criteria.settings import IS, IS_NOT, IS_VALID, IS_NOT_VALID
from lfs.discounts.models import Discount
from lfs.manufacturer.models import Manufacturer
from lfs.order.models import Order
from lfs.order.settings import CLOSED

try:
    from lfs.criteria.models.criteria import (Criterion,
                                              CriterionRegistrator,
                                              NumberCriterion)
except ImportError:
    Criterion = monkey.Criterion
    CriterionRegistrator = monkey.CriterionRegistrator
    NumberCriterion = monkey.NumberCriterion


IS_AUTHENTICATED = 20
IS_ANONYMOUS = 21

USER_OPERATORS = (
    (IS, _(u"Is")),
    (IS_NOT, _(u"Is not")),
    (IS_AUTHENTICATED, _(u"Authenticated")),
    (IS_ANONYMOUS, _(u"Anonymous")),
)

CHOICE_OPERATORS = (
    (IS, _(u"Is")),
    (IS_NOT, _(u"Is not")),
)

VALID_CHOICE_OPERATORS = (
    (IS_VALID, _(u"Is valid")),
    (IS_NOT_VALID, _(u"Is not valid")),
)


class OrderCountCriterion(NumberCriterion):
    """A criterion for the cart price.
    """
    order_count = models.IntegerField(_(u"Order сount"), default=0)
    value_attr = 'order_count'
    content_type = u"order_count"
    name = _(u"Order count")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.

        If product is given the order_count is taken from the all orders with this product and user,
        overwise all orders from this user.
        """
        filters = {}
        if product is not None:
            filters['items__product'] = product
        if request.user.is_authenticated():
            filters['user'] = request.user
        else:
            filters['session'] = request.session.session_key

        #count only closed orders
        filters['state'] = CLOSED

        order_count = Order.objects.filter(**filters).count()

        return self.test_value(order_count)


class GroupCriterion(Criterion):
    """A criterion for user content objects
    """
    groups = models.ManyToManyField(Group)
    value_attr = 'groups'
    multiple_value = True

    content_type = u"group"
    name = _(u"Group")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        user = request.user
        if user.is_anonymous():
             return False

        user_groups = user.groups.all().values('id')
        groups = self.groups.filter(id__in=user_groups)
        return groups.exists()

    def as_html(self, request, position):
        """Renders the criterion as html in order to be displayed within several
        forms.
        """
        users = []
        selected_groups = self.groups.all()
        for g in Group.objects.all():
            if g in selected_groups:
                selected = True
            else:
                selected = False

            users.append({
                "id" : g.id,
                "name" : g.name,
                "selected" : selected,
            })

        return render_to_string("manage/criteria/group_criterion.html", RequestContext(request, {
            "id" : "ex%s" % self.id,
            "operator" : self.operator,
            "groups" : users,
            "position" : position,
            "content_type" : self.content_type,
            "types" : CriterionRegistrator.items(),
        }))


class CategoryCriterion(Criterion):
    """A criterion for the shipping category.
    """
    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS)
    categories = models.ManyToManyField(Category, verbose_name=_(u"Category"))
    value_attr = 'categories'
    multiple_value = True

    def __unicode__(self):
        values = []
        for value in self.value.all():
            values.append(value.name)

        return u"%s %s %s" % (self.name,
                              self.get_operator_display(),
                              u", ".join(values))

    content_type = u"category"
    name = _(u"Category")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        if product:
            result = product.get_category() in self.categories.all()
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False

            categories = set()
            for item in cart.items():
                categories.add(item.product.get_category())

            result = bool(categories.intersection(self.categories.all()))

        if self.operator == IS:
            return result
        else:
            return not result

    def as_html(self, request, position):
        """Renders the criterion as html in order
        to be displayed within several forms.
        """

        categories = []
        self_categories = self.categories.all()
        for category in Category.objects.all():
            if category in self_categories:
                selected = True
            else:
                selected = False

            categories.append({
                "id": category.id,
                "name": category.name,
                "selected": selected,
                "level": category.level,
            })

        return render_to_string("manage/criteria/category_criterion.html",
          RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "value": self.value,
            "position": position,
            "categories": categories,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))


class ProductCriterion(Criterion):
    """A criterion for the shipping category.
    """
    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS)
    products = models.ManyToManyField(Product, verbose_name=_(u"Product"))
    value_attr = 'products'
    multiple_value = True

    def __unicode__(self):
        values = []
        for value in self.value.all():
            values.append(value.name)

        return u"%s %s %s" % (self.name,
                              self.get_operator_display(),
                              u", ".join(values))

    content_type = u"product"
    name = _(u"Product")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        if product:
            result = product in self.products.all()
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False

            products = set(item.product for item in cart.items()
                           if item.product)

            result = bool(products.intersection(self.products.all()))

        if self.operator == IS:
            return result
        else:
            return not result

    def as_html(self, request, position):
        """Renders the criterion as html in order
        to be displayed within several forms.
        """

        products = Product.objects.all()
        self_products = self.products.all()

        for product in products:
            product.selected = product in self_products

        return render_to_string("manage/criteria/product_criterion.html",
          RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "value": self.value,
            "position": position,
            "products": products,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))


class OrderCompositionCriterion(Criterion):
    """A criterion for the shipping category.
    """
    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS,
                                           default=IS)
    categories = models.ManyToManyField(Category,
                                        through="CompositionCategory",
                                        verbose_name=_(u"Category"))
    value_attr = 'categories'
    multiple_value = True

    criteria_objects = generic.GenericRelation(CriteriaObjects,
        object_id_field="criterion_id", content_type_field="criterion_type")

    def __unicode__(self):
        values = []
        for value in self.value.all():
            values.append(value.name)

        return u"%s %s %s" % (self.name,
                              self.get_operator_display(),
                              u", ".join(values))

    content_type = u"composition_category"
    name = _(u"Composition")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        #content_object = self.criteria_objects.filter()[0].content
        result = True
        cart = get_cart(request)
        if cart is None or not cart.items().exists():
            return False
        compositions = CompositionCategory.objects.filter(criterion=self)

        for composition in compositions:
            amount = 0
            for item in cart.items().filter(
                                product__categories=composition.category):
                amount += item.amount
            if amount < composition.amount:
                result = False
                break

        if self.operator == IS:
            return result
        else:
            return not result

    def as_html(self, request, position):
        """Renders the criterion as html in order
        to be displayed within several forms.
        """

        compositions = CompositionCategory.objects.filter(criterion=self)\
                                                  .values('amount',
                                                          'category')
        formset = CompositionCategoryFormSet(initial=compositions)

        template = "manage/criteria/composition_category_criterion.html"
        return render_to_string(template, RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "position": position,
            "compositions": compositions,
            "formset": formset,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))

    @classmethod
    def create(cls, operator, value, request=None):

        c = cls.objects.create()
        if request.method == 'POST' and 'form-0-amount' in request.POST:
            formset = CompositionCategoryFormSet(request.POST)
            for form in formset.forms:
                if form.is_valid():
                    if not 'category' in form.cleaned_data:
                        continue
                    if form.cleaned_data['DELETE']:
                        continue
                    form.instance.criterion = c
                    form.save()
        return c


class CompositionCategory(models.Model):

    criterion = models.ForeignKey(OrderCompositionCriterion,
                                  verbose_name=_('Composition'),
                                  related_name="compositions")
    category = models.ForeignKey(Category, verbose_name=_('Category'))
    amount = models.IntegerField(verbose_name=_('Amount'), default=1)

    def __unicode__(self):
        return u'%s-%s' % (self.category.name, self.amount)


class CompositionCategoryForm(forms.ModelForm):

    class Meta:
        model = CompositionCategory
        fields = ['category', 'amount']

CompositionCategoryFormSet = formset_factory(form=CompositionCategoryForm,
                                             extra=1,
                                             can_delete=True)


class DiscountCriterion(Criterion):
    """A criterion for the payment method.
    """
    operator = models.PositiveIntegerField(_(u"Operator"),
                                           choices=VALID_CHOICE_OPERATORS,
                                           default=IS_NOT_VALID)
    discounts = models.ManyToManyField(Discount, verbose_name=_(u"Discount"))
    value_attr = 'discounts'
    multiple_value = True

    criteria_objects = generic.GenericRelation(CriteriaObjects,
        object_id_field="criterion_id", content_type_field="criterion_type")

    def __unicode__(self):
        values = []
        for value in self.value.all():
            values.append(value.name)

        return u"%s %s %s" % (self.name,
                              self.get_operator_display(),
                              u", ".join(values))

    content_type = u"discounts"
    name = _(u"Discount")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        from lfs.criteria.utils import is_valid
        content_object = self.criteria_objects.filter()[0].content
        if isinstance(content_object, Discount):
            is_discount = True
        else:
            is_discount = False

        if is_discount and self.operator == IS_VALID:
            for d in self.discounts.all():
                if not d.active:
                    continue
                if not is_valid(request, d, product):
                    return False
            return True
        elif is_discount and self.operator == IS_NOT_VALID:
            for d in self.discounts.all():
                if not d.active:
                    continue
                if is_valid(request, d, product):
                    return False
            return True

        else:
            return False

    def as_html(self, request, position):
        """Renders the criterion as html in order
        to be displayed within several forms.
        """
        cr_objects = self.criteria_objects.all()
        self_discounts = self.discounts.all()
        discounts = []
        all_discounts = Discount.objects.all().order_by('position')
        if cr_objects.exists():
            content_object = cr_objects[0].content
            all_discounts = all_discounts.exclude(id=content_object.id)
        for d in all_discounts:
            if d in self_discounts:
                selected = True
            else:
                selected = False
            discounts.append({
                "id": d.id,
                "name": d.name,
                "selected": selected,
            })

        return render_to_string("manage/criteria/discounts_criterion.html",
                                RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "value": self.value,
            "position": position,
            "discounts": discounts,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))


class OrderSummCriterion(NumberCriterion):

    order_summ = models.IntegerField(_(u"Order summ"), default=0)
    value_attr = 'order_summ'
    content_type = u"order_summ"
    name = _(u"Order summ")

    def is_valid(self, request, product=None):

        if product is not None:
            filters = {'items__product': product}
        else:
            filters = {}

        if request.user.is_authenticated():
            filters['user'] = request.user
        else:
            filters['session'] = request.session.session_key

        order_summ = Order.objects.filter(**filters)\
                          .aggregate(sum_price=Sum('price'))['sum_price']
        return self.test_value(order_summ)


class ManufacturerCriterion(Criterion):
    """A criterion for the shipping category.
    """
    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS)
    manufacturers = models.ManyToManyField(Manufacturer,
                                           verbose_name=_(u"Manufacturer"))

    value_attr = 'manufacturers'
    multiple_value = True

    def __unicode__(self):
        values = []
        for value in self.value.all():
            values.append(value.name)

        return u"%s %s %s" % (self.name,
                              self.get_operator_display(),
                              u", ".join(values))

    content_type = u"manufacturer"
    name = _(u"Manufacturer")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        if product:
            mnf = product.get_manufacturer()
            result = mnf in self.manufacturers.all()
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False

            manufacturers = set()
            for item in cart.items():
                manufacturers.add(item.product.get_manufacturer())

            result = bool(manufacturers.intersection(self.manufacturers.all()))

        if self.operator == IS:
            return result
        else:
            return not result

    def as_html(self, request, position):
        """Renders the criterion as html in order
        to be displayed within several forms.
        """

        manufacturers = []
        self_manufacturers = self.manufacturers.all()
        for manufacturer in Manufacturer.objects.all().order_by('name'):
            if manufacturer in self_manufacturers:
                selected = True
            else:
                selected = False

            manufacturers.append({
                "id": manufacturer.id,
                "name": manufacturer.name,
                "selected": selected,
            })

        return render_to_string("manage/criteria/manufacturer_criterion.html",
                                RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "value": self.value,
            "position": position,
            "manufacturers": manufacturers,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))


class TimeCriterion(NumberCriterion):

    time = models.TimeField(_(u"Time"), default=datetime.time(0, 0))
    value_attr = 'time'
    content_type = u"time"
    name = _(u"Time")
    widget = forms.TimeInput

    @classmethod
    def create(self, operator, value, request=None):

        value = forms.TimeField().to_python(value)

        c = self.objects.create(operator=operator)
        c.value = value
        c.save()
        return c

    def is_valid(self, request, product=None):
        return self.test_value(datetime.datetime.now().time())


class CartAmountCriterion(NumberCriterion):

    amount = models.IntegerField(_(u"Сart amount"), default=0)
    value_attr = u'amount'
    content_type = u"amount"
    name = _(u"Cart amount")

    def is_valid(self, request, product=None):
        cart = get_cart(request)
        if not cart or not cart.items():
            return False
        amount = 0
        for item in cart.items():
            amount += item.amount
        return self.test_value(amount)


class MaxWeightCriterion(NumberCriterion):

    max_weight = models.IntegerField(_(u"Max weight"), default=0.)
    value_attr = u'max_weight'
    content_type = u"max_weight"
    name = _(u"Max weight")

    def is_valid(self, request, product=None):

        if product:
            return self.test_value(product.weight)

        cart = get_cart(request)
        if not cart or not cart.items():
            return False

        max_weight = cart.items()\
                         .aggregate(max_weight=Max('product__weight'))
        max_weight = max_weight['max_weight']
        return self.test_value(max_weight)


class ForSaleCriterion(Criterion):

    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS)
    for_sale = models.BooleanField(verbose_name=_(u"For sale"), default=True)
    value_attr = 'for_sale'
    content_type = 'for_sale'
    name = _(u"For sale")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        if product:
            result = product.get_for_sale()
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False

            result = any(item.product.get_for_sale()
                         for item in cart.items())

        if self.operator == IS:
            return result
        else:
            return not result


class ManualDeliveryTimeCriterion(Criterion):

    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=CHOICE_OPERATORS)
    manual_delivery_time = models.BooleanField(
                               verbose_name=_(u"Manual delivery time"),
                               default=True)
    value_attr = 'manual_delivery_time'
    content_type = 'manual_delivery_time'
    name = _(u"Manual delivery time")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        if product:
            result = product.manual_delivery_time
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False

            result = any(item.product.manual_delivery_time
                         for item in cart.items())

        if self.operator == IS:
            return result
        else:
            return not result


class FullUserCriterion(Criterion):
    """A criterion for user content objects
    """

    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=USER_OPERATORS)
    users = models.ManyToManyField(User)
    value_attr = 'users'
    multiple_value = True

    content_type = u"full_user"
    name = _(u"User (advanced)")

    def is_valid(self, request, product=None):
        """Returns True if the criterion is valid.
        """
        operator = self.operator
        user = request.user
        if operator == IS_AUTHENTICATED:
            return user.is_authenticated()
        elif operator == IS_ANONYMOUS:
            return user.is_anonymous()
        else:
            result = user in self.users.all()
            return result if operator == IS else not result

    def as_html(self, request, position):
        """Renders the criterion as html in order to be displayed
           within several forms.
        """
        users = []
        selected_users = self.users.all()
        # TODO check permission manage shop
        for user in User.objects.filter(is_active=True):
            selected = user in selected_users

            users.append({
                "id": user.id,
                "username": user.username,
                "selected": selected,
            })

        return render_to_string("manage/criteria/full_user_criterion.html",
          RequestContext(request, {
            "id": "ex%s" % self.id,
            "operator": self.operator,
            "users": users,
            "position": position,
            "content_type": self.content_type,
            "types": CriterionRegistrator.items(),
        }))

    @classmethod
    def create(cls, operator, value, request=None):
        c = cls.objects.create()
        c.operator = operator
        for user in User.objects.filter(pk__in=value):
            c.users.add(user)
        c.save()
        return c


class ProfitCriterion(NumberCriterion):

    profit = models.FloatField(_(u"Profit"), default=0.)
    value_attr = u'profit'
    content_type = u"profit"
    name = _(u"Profit")

    def is_valid(self, request, product=None):

        if product is not None:
            products = [product]
        else:
            cart = get_cart(request)
            if cart is None or not cart.items().exists():
                return False
            product_ids = list(cart.items().values_list('product', flat=True))
            products = Product.objects.filter(id__in=product_ids)

        profit = 0.
        for product in products:
            price = product.get_price()
            d_price = product.localproduct.get_best_distributor_price()
            profit += (price - d_price)

        return self.test_value(profit)
