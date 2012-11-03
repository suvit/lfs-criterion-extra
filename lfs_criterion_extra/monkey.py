# python imports
from datetime import datetime

# django imports
from django.contrib.auth.decorators import permission_required
from django.db import models
from django.db.models.base import ModelBase
from django.http import HttpResponse
from django.forms import TextInput
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

#lfs imports
from lfs.criteria.models import CriteriaObjects
from lfs.criteria.models.criteria import Criterion as BaseCriterion
from lfs.criteria.models.criteria import CountryCriterion
from lfs.criteria.models.criteria import CombinedLengthAndGirthCriterion
from lfs.criteria.models.criteria import CartPriceCriterion
from lfs.criteria.models.criteria import DistanceCriterion
from lfs.criteria.models.criteria import HeightCriterion
from lfs.criteria.models.criteria import LengthCriterion
from lfs.criteria.models.criteria import PaymentMethodCriterion
from lfs.criteria.models.criteria import ShippingMethodCriterion
from lfs.criteria.models.criteria import UserCriterion
from lfs.criteria.models.criteria import WidthCriterion
from lfs.criteria.models.criteria import WeightCriterion
from lfs.criteria.settings import EQUAL
from lfs.criteria.settings import LESS_THAN
from lfs.criteria.settings import LESS_THAN_EQUAL
from lfs.criteria.settings import GREATER_THAN
from lfs.criteria.settings import GREATER_THAN_EQUAL
from lfs.criteria.settings import NUMBER_OPERATORS

#imports for patching
import lfs.criteria.utils
import lfs.manage.views.criteria


# patching models
class CriterionRegistrator(ModelBase):

    types = dict()

    def __new__(cls, name, bases, attrs):
        abstract = getattr(attrs.get('Meta'), 'abstract', False)
        new_class = super(CriterionRegistrator,
                     cls).__new__(cls, name, bases, attrs)
        if not abstract:
            cls.register(new_class)
        return new_class

    @classmethod
    def register(cls, new_class):
        if new_class.content_type is None:
            logger.error('registering None criterion type %s' % new_class)
        cls.types[new_class().content_type] = new_class

    @classmethod
    def items(cls):
        return [{'id': item().content_type,
                 'name': item().name} for item in cls.types.values()]


CriterionRegistrator.register(CountryCriterion)
CountryCriterion.multiple_value = True
CriterionRegistrator.register(CombinedLengthAndGirthCriterion)
CriterionRegistrator.register(CartPriceCriterion)
CriterionRegistrator.register(DistanceCriterion)
CriterionRegistrator.register(HeightCriterion)
CriterionRegistrator.register(LengthCriterion)
CriterionRegistrator.register(PaymentMethodCriterion)
PaymentMethodCriterion.multiple_value = True
CriterionRegistrator.register(ShippingMethodCriterion)
ShippingMethodCriterion.multiple_value = True
CriterionRegistrator.register(UserCriterion)
UserCriterion.multiple_value = True
UserCriterion.operator = None  # XXX error in django lfs 0.7
CriterionRegistrator.register(WidthCriterion)
CriterionRegistrator.register(WeightCriterion)
#print CriterionRegistrator.types


class Criterion(models.Model, BaseCriterion):

    __metaclass__ = CriterionRegistrator

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"%s: %s %s" % (self.name,
                               self.get_operator_display(),
                               self.value)

    def get_operator_display(self):
        return unicode(self.operator) # TODO

    value_attr = None

    def get_value(self):
        return getattr(self, self.value_attr)
    def set_value(self, value):
        setattr(self, self.value_attr, value)
    value = property(get_value, set_value)

    multiple_value = False

    operator = None
    name = None
    content_type = None
    widget = TextInput

    def as_html(self, request, position):
        """Renders the criterion as html in order to displayed it within several
        forms.
        """
        template = "manage/criteria/%s_criterion.html" % self.content_type

        widget = getattr(self, 'widget', TextInput)
        if isinstance(widget, type):
            widget = widget()

        if self.id is None:
           cid = "ex%s" % datetime.now().strftime("%s")
        else:
           cid = "ex%s" % self.id

        return render_to_string(template, RequestContext(request, {
            "id" : cid,
            "operator" : self.operator,
            "widget_value" : widget.render(name='value-%s' % cid,
                                           value=self.value,
                                           attrs={'class': "criterion-value",
                                                  'id': 'text-%s' % cid}),
            "position" : position,
            "content_type" : self.content_type,
            "types" : CriterionRegistrator.items(),
        }))

    def is_valid(self, request, product=None):
        raise NotImplementedError()

    @classmethod
    def create(cls, operator, value, request=None):
        if not cls.multiple_value:
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0.0

        c = cls.objects.create(operator=operator)
        c.value = value
        c.save()
        return c


class NumberCriterion(Criterion):

    operator = models.PositiveIntegerField(_(u"Operator"),
                                           blank=True, null=True,
                                           choices=NUMBER_OPERATORS)

    class Meta:
        abstract = True

    def test_value(self, value):
        if self.operator == LESS_THAN and (value < self.value):
            return True
        if self.operator == LESS_THAN_EQUAL and (value <= self.value):
            return True
        if self.operator == GREATER_THAN and (value > self.value):
            return True
        if self.operator == GREATER_THAN_EQUAL and (value >= self.value):
            return True
        if self.operator == EQUAL and (value == self.value):
            return True

        return False

# patching views
@permission_required("core.manage_shop")
def add_criterion(request):
    return change_criterion_form(request)
add_criterion.patched = True
lfs.manage.views.criteria.add_criterion = add_criterion


@permission_required("core.manage_shop")
def change_criterion_form(request):
    """Changes the changed criterion form to the given type (via request body)
    form.

    This is called via an AJAX request. The result is injected into the right
    DOM node.
    """
    type = request.POST.get("type", "price")

    # create a (pseudo) unique id for the the new criterion form fields. This
    # are the seconds since Epoch
    now = datetime.now()
    criterion = CriterionRegistrator.types[type]()
    criterion.id = "%s%s" % (now.strftime("%s"), now.microsecond)
    return HttpResponse(criterion.as_html(request, None))
change_criterion_form.patched = True
lfs.manage.views.criteria.change_criterion_form = change_criterion_form


# patching utils
def save_criteria(request, object):
    """Saves the criteria for the given object. The criteria are passed via
    request body.
    """
    # First we delete all existing criteria objects for the given object.
    for co in object.criteria_objects.all():
        co.criterion.delete()
        co.delete()


    # Then we add all passed criteria to the shipping method.
    for key, type_ in request.POST.items():
        if key.startswith("type"):
            try:
                id = key.split("-")[1]
            except KeyError:
                continue

            # Get the operator and value for the calculated id
            operator = request.POST.get("operator-%s" % id)

            criterion_type = CriterionRegistrator.types[type_]
            if getattr(criterion_type, 'multiple_value', False):
                value = request.POST.getlist("value-%s" % id)
            else:
                value = request.POST.get("value-%s" % id)

            if hasattr(criterion_type, 'create'):
                c = criterion_type.create(operator, value, request)
            else:
                # old criterions
                c = criterion_type.objects.create(operator=operator)
                if type_ == "country":
                    c.countries = value
                elif type_ == "payment_method":
                    c.payment_methods = value
                elif type_ == "shipping_method":
                    c.shipping_methods = value
                elif type_ == "user":
                    c.users = value
                elif type_ == "combinedlengthandgirth":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.clag = value
                elif type_ == "price":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.price = value
                elif type_ == "height":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.height = value
                elif type_ == "length":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.length = value
                elif type_ == "width":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.width = value
                elif type_ == "weight":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.weight = value
                elif type_ == "distance":
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        value = 0.0
                    c.distance = value

                c.save()

            position = request.POST.get("position-%s" % id)
            CriteriaObjects.objects.create(content=object,
                                           criterion=c,
                                           position=position)

save_criteria.patched = True
lfs.criteria.utils.save_criteria = save_criteria
