from django.contrib import admin
from .models import Store,Membership,CatalogJob
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display=("id","name","active")
    search_fields=("name",)
@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display=("user","store","role")
    list_filter=("role",)
@admin.register(CatalogJob)
class JobAdmin(admin.ModelAdmin):
    list_display=("id","store","status","created_at")
    list_filter=("status",)
    readonly_fields=("baseline","supplier_update","submitted_by","store")
    def has_add_permission(self,request):return False
