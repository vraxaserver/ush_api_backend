from django.contrib import admin
from accounts.models import UserType

class SpaCenterRestrictedAdminMixin:
    """
    Mixin to restrict admin access to objects based on the user's assigned spa center.
    Applied to Models that have a 'spa_center' field or a related path to it.
    """
    
    spa_center_field = "spa_center"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        if request.user.user_type == UserType.BRANCH_MANAGER:
            if request.user.spa_center_id:
                filter_kwargs = {self.spa_center_field: request.user.spa_center_id}
                return qs.filter(**filter_kwargs)
            else:
                # Manager but no spa center assigned - see nothing
                return qs.none()
            
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and request.user.user_type == UserType.BRANCH_MANAGER:
            if db_field.name == "spa_center":
                if request.user.spa_center:
                    kwargs["queryset"] = db_field.related_model.objects.filter(id=request.user.spa_center_id)
                else:
                    kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Automatically assign spa_center if not set and user is a manager."""
        if not request.user.is_superuser and request.user.user_type == UserType.BRANCH_MANAGER:
            if hasattr(obj, "spa_center") and not getattr(obj, "spa_center", None):
                obj.spa_center = request.user.spa_center
        super().save_model(request, obj, form, change)
