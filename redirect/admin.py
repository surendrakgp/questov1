from django.conf import settings
from django.contrib import admin
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from redirect.models import (#CanonicalMicrosite,
	CompanyEmail,
    CustomExcludedViewSource, DestinationManipulation, EmailRedirectLog,
    ExcludedViewSource, ViewSource)


#
# Admin Filters
#


class MultiSearchFilter(admin.FieldListFilter):
    """
    Allows the selection of multiple values in a Django admin filter list.
    """
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(MultiSearchFilter, self).__init__(field, request, params, model,
                                                model_admin, field_path)
        self.filter_parameters = request.GET.get(self.field_path, None)
        self.field_choices = field.get_choices(include_blank=False)

    def expected_parameters(self):
        return [self.field_path]

    def values(self):
        values = []
        value = self.used_parameters.get(self.field_path, None)
        if value:
            values = value.split(',')
        return values

    def queryset(self, request, queryset):
        values = self.values()
        filter_query = {'%s__in' % self.field_path : values}
        if values:
            return queryset.filter(**filter_query)
        else:
            return queryset

    def choices(self, cl):
        yield {
            'selected': self.filter_parameters is None,
            'query_string': cl.get_query_string({}, [self.field_path]),
            'display': _('All')}

        for name, value in self.field_choices:
            selected = name in self.values()
            name_list = set(self.values())
            if selected:
                name_list.remove(name)
            else:
                name_list.add(name)
            if name_list:
                query_string = cl.get_query_string(
                    {self.field_path: ','.join(name_list)})
            else:
                query_string = cl.get_query_string({}, [self.field_path])
            yield {
                'selected': selected,
                'query_string': query_string,
                'display': value}


class BlankValueListFilter(admin.SimpleListFilter):
    """
    Filters :field_name: based on whether or not that field has valuable text
    or is [Null, '[blank]', or '']

    Should only be used via a subclass which defines title, parameter_name,
    and field_name
    """
    title = ''
    parameter_name = ''

    field_name = ''

    def lookups(self, request, model_admin):
        return (
            ('Blank', _('Field is blank')),
            ('Exists', _('Field exists')))

    def queryset(self, request, queryset):
        query = Q(**{self.field_name: '[blank]'}) | \
                Q(**{self.field_name: ''}) | \
                Q(**{'%s__isnull' % self.field_name: True})
        if self.value() == 'Blank':
            return queryset.filter(query)
        elif self.value() == 'Exists':
            return queryset.exclude(query)
        else:
            return queryset


class BlankValue1ListFilter(BlankValueListFilter):
    title = _('Value 1')
    parameter_name = 'value_1'
    field_name='value_1'


class BlankValue2ListFilter(BlankValueListFilter):
    title = _('Value 2')
    parameter_name = 'value_2'
    field_name='value_2'


class ExcludedViewSourceFilter(admin.SimpleListFilter):
    title = _('excluded')
    parameter_name = 'ms'
    def lookups(self, request, model_admin):
        return (('Yes', _('Yes')),
                ('No', _('No')))

    def queryset(self, request, queryset):
        if getattr(self, 'view_source_id', None) is not None:
            param = 'view_source_id'
        else:
            param = 'view_source'
        filter_dict = {'%s__in' % param: settings.EXCLUDED_VIEW_SOURCES}
        if self.value() == 'Yes':
            return queryset.filter(**filter_dict)
        elif self.value() == 'No':
            return queryset.exclude(**filter_dict)
        else:
            return queryset


#
# Model Admins
#


class CanonicalMicrositeAdmin(admin.ModelAdmin):
    list_display = ['buid', 'canonical_microsite_url']
    search_fields = ['buid', 'canonical_microsite_url']


class CompanyEmailAdmin(admin.ModelAdmin):
    list_display = ['buid', 'email']
    search_fields = ['=buid', 'email']


class CustomExcludedViewSourceAdmin(admin.ModelAdmin):
    list_display = ['buid', 'get_vs_name']
    search_fields = ['buid', 'view_source']


class DestinationManipulationAdmin(admin.ModelAdmin):
    list_filter = ['action_type',
                   ('action', MultiSearchFilter),
                   BlankValue1ListFilter,
                   BlankValue2ListFilter,
                   ExcludedViewSourceFilter]
    search_fields = ['=buid', '=view_source']
    list_display = ['buid', 'get_view_source_name', 'action_type',
                    'action', 'value_1', 'value_2']

class EmailRedirectLogAdmin(admin.ModelAdmin):
    list_display = ['buid', 'from_addr', 'to_addr', 'sent']
    search_fields = ['=buid', 'from_addr', 'to_addr']


class ExcludedViewSourceAdmin(admin.ModelAdmin):
    list_display = ['get_vs_cell']
    search_fields = ['=view_source']


class ViewSourceAdmin(admin.ModelAdmin):
    list_display = ['view_source_id', 'name', 'is_excluded']
    list_filter = [ExcludedViewSourceFilter]
    search_fields = ['=view_source_id', 'name']

    def get_readonly_fields(self, request, obj=None):
        """
        If a new object is being created, leave view_source_id editable.
        If the user is viewing an existing object, make it read-only.
        """
        if obj:
            return self.readonly_fields + ('view_source_id',)
        else:
            return []


#admin.site.register(CanonicalMicrosite, CanonicalMicrositeAdmin)
admin.site.register(CompanyEmail, CompanyEmailAdmin)
admin.site.register(CustomExcludedViewSource, CustomExcludedViewSourceAdmin)
admin.site.register(DestinationManipulation, DestinationManipulationAdmin)
admin.site.register(EmailRedirectLog, EmailRedirectLogAdmin)
admin.site.register(ExcludedViewSource, ExcludedViewSourceAdmin)
admin.site.register(ViewSource, ViewSourceAdmin)
