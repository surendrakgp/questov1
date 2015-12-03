from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
import json


def get_fields(request):
    model = request.GET.get('model')
    content_type = ContentType.objects.get(pk=model)
    model_class = content_type.model_class()
    return HttpResponse(json.dumps(getattr(model_class, 'EVENT_FIELDS', {})))