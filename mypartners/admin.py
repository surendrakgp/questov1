from django.contrib import admin

from django_extensions.admin import ForeignKeyAutocompleteAdmin

from mypartners.models import (Partner, Contact, CommonEmailDomain,
                               OutreachEmailDomain)

from .models import *
# from mydashboard.admin import company_user_name


# class OutreachEmailDomainAdmin(ForeignKeyAutocompleteAdmin):
#     related_search_fields = {
#         'company': ('name',)
#     }

#     related_string_Functions = {
#         'company': company_user_name
#     }

#     search_fields = ['company__name', 'domain']

#     class Meta:
#         model = OutreachEmailDomain

#     class Media:
#         js = ('django_extensions/js/jquery-1.7.2.min.js', )


admin.site.register(Partner)
admin.site.register(Contact)
admin.site.register(CommonEmailDomain)
admin.site.register(OutreachEmailDomain#, OutreachEmailDomainAdmin
	)


admin.site.register(Status)
admin.site.register(PartnerLibrary)