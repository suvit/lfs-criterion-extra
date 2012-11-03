# -*- coding: utf-8 -*-
import re
from django.template import Library

from lfs_criterion_extra.models import CriterionRegistrator


register = Library()


@register.inclusion_tag('manage/criteria/types.html', takes_context=True)
def types(context):
    types = context.get('types')
    if types is None:
        context['types'] = CriterionRegistrator.items()
    content_type = context.get('content_type')
    if types is None:
        id = context['id']
        context['content_type'] = re.sub("\d+", "", id)
    return context