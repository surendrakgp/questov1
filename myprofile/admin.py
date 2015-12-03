from django.contrib import admin
from .models import *
# Register your models here.

class BasicinfoAdmin(admin.ModelAdmin):
	prepopulated_fields = {"slug": ("name",)}
	list_display = ('name','slug','mobile','Job_Search_Status','desired_Salary','Profile_Pic','updated')



admin.site.register(ProfileUnits)
admin.site.register(Basicinfo,BasicinfoAdmin)
admin.site.register(Experience)
admin.site.register(Education)
admin.site.register(Social)
admin.site.register(Skill)
