from django.contrib import admin
from .models import PreplotLine, Sequence, AcquisitionShotPoint, PreplotShotPoints


@admin.register(PreplotLine)
class PreplotLineAdmin(admin.ModelAdmin):
    list_display = ('preplot',)
    search_fields = ('preplot',)
    
    def get_queryset(self, request):
        # Use select_related() to reduce the number of database queries
        return super().get_queryset(request).select_related()
    
    def has_delete_permission(self, request, obj=None):
        # Disable bulk delete from changelist view
        if not obj:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        # Delete related objects in chunks
        # First delete PreplotShotPoints
        obj.ppsp.all().delete()
        # Then delete Sequences and their related AcquisitionShotPoints
        for sequence in obj.sequence.all():
            sequence.details.all().delete()
        obj.sequence.all().delete()
        # Finally delete the PreplotLine
        obj.delete()

@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ('linename',)
    search_fields = ('linename',)  
    list_filter = ('preplot',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('preplot')

@admin.register(AcquisitionShotPoint)
class AcquisitionShotPointAdmin(admin.ModelAdmin):
    list_display = ('sp',)
    search_fields = ('sp',)
    list_filter = ('sequence',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sequence')

@admin.register(PreplotShotPoints)
class PreplotShotPointsAdmin(admin.ModelAdmin):
    list_display = ('shotpoint',)
    search_fields = ('shotpoint',)
    list_filter = ('preplot',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('preplot')
