from django.contrib import admin
from .models import PreplotLine, Sequence, AcquisitionShotPoint, PreplotShotPoints
from django.utils.html import format_html


class SequenceInline(admin.TabularInline):
    model = Sequence
    extra = 0
    fields = ['linename', 'type', 'pass_number', 'sequence_number', 'filename', 'completion_status']
    readonly_fields = [
        'type', 'pass_number', 'sequence_number', 'linename', 'filename', 'completion_status'
    ]
    verbose_name = "Associated Sequence"
    verbose_name_plural = "Associated Sequences"

    def has_add_permission(self, request, obj=None):
        return False
        
    def completion_status(self, obj):
        if not obj.preplot:
            return "No preplot"
        total_preplot_points = obj.preplot.ppsp.count()
        if total_preplot_points == 0:
            return "No preplot points"
        acquired_points = obj.details.count()
        completion = (acquired_points / total_preplot_points * 100) if total_preplot_points > 0 else 0
        return f"{completion:.1f}% complete"


@admin.register(PreplotLine)
class PreplotLineAdmin(admin.ModelAdmin):
    list_display = ('preplot', 'display_sequences', 'completion_status', 'force_completed')
    list_filter = ('force_completed',)
    actions = ['mark_completed', 'mark_uncompleted']
    inlines = [SequenceInline]
    
    def display_sequences(self, obj):
        sequences = obj.sequence.all()
        if not sequences:
            return 'No sequences'

        sequence_info = []
        for seq in sequences:
            # Calculate completion percentage for this sequence
            total_preplot_points = obj.ppsp.count()
            acquired_points = seq.details.count()
            completion = (acquired_points / total_preplot_points * 100) if total_preplot_points > 0 else 0

            sequence_info.append(
                f"{seq.linename} (Pass {seq.pass_number}, {completion:.1f}% complete)"
            )

        return format_html('<br>'.join(sequence_info))
        
    display_sequences.short_description = 'Sequences & Status'
    # display_sequences.short_description = 'Sequences'

    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related('sequence')
        # Add debug print
        for obj in qs:
            print(f"PreplotLine {obj.preplot} sequences:",
                  list(obj.sequence.all()))
        return qs

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

    def completion_status(self, obj):
        is_completed = obj.calculate_completion_status()
        if is_completed:
            return format_html('<img src="/static/admin/img/icon-yes.svg" alt="Completed">')
        return format_html('<img src="/static/admin/img/icon-no.svg" alt="Not Completed">')
        
    completion_status.short_description = 'Completed'
    
    def mark_completed(self, request, queryset):
        queryset.update(force_completed=True)
        
    mark_completed.short_description = "Mark selected lines as completed"
    
    def mark_uncompleted(self, request, queryset):
        queryset.update(force_completed=False)
        
    mark_uncompleted.short_description = "Mark selected lines as uncompleted"
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # editing an existing object
            return readonly_fields + ('completion_status',)
        return readonly_fields
        
    fieldsets = (
        (None, {
            'fields': ('preplot', 'loaded', 'force_completed')
        }),
        ('Shot Point 1', {
            'fields': ('shotpoint1', 'eastings1', 'northings1', 'latitude1', 'longitude1')
        }),
        ('Shot Point 2', {
            'fields': ('shotpoint2', 'eastings2', 'northings2', 'latitude2', 'longitude2')
        }),
    )


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ('linename', 'sequence_number', 'type', 'pass_number')
    search_fields = ('linename', )
    list_filter = ('preplot', )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('preplot')


@admin.register(AcquisitionShotPoint)
class AcquisitionShotPointAdmin(admin.ModelAdmin):
    list_display = ('sp', )
    search_fields = ('sp', )
    list_filter = ('sequence', )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sequence')


@admin.register(PreplotShotPoints)
class PreplotShotPointsAdmin(admin.ModelAdmin):
    list_display = ('shotpoint', )
    search_fields = ('shotpoint', )
    list_filter = ('preplot', )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('preplot')
