from django.contrib import admin
from .models import PreplotLine, Sequence, AcquisitionShotPoint, PreplotShotPoints


@admin.register(PreplotLine)
class PreplotLineAdmin(admin.ModelAdmin):
    list_display = ('preplot',)
    search_fields = ('preplot',)

@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ('linename',)
    search_fields = ('linename',)  
    list_filter = ('preplot',)

@admin.register(AcquisitionShotPoint)
class AcquisitionShotPointAdmin(admin.ModelAdmin):
    list_display = ('sp',)
    search_fields = ('sp',)
    list_filter = ('sequence',)

@admin.register(PreplotShotPoints)
class PreplotShotPointsAdmin(admin.ModelAdmin):
    list_display = ('shotpoint',)
    search_fields = ('shotpoint',)
    list_filter = ('preplot',)
