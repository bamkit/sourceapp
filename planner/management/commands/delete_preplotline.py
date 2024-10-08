from django.core.management.base import BaseCommand
from planner.models import PreplotLine

class Command(BaseCommand):
    help = 'Delete all PreplotLine records in batches to avoid crashing'

    def handle(self, *args, **kwargs):
        batch_size = 1000
        total_deleted = 0

        # Keep looping while there are still records to delete
        while PreplotLine.objects.exists():
            # Get the IDs of the batch_size number of records
            ids = list(PreplotLine.objects.values_list('id', flat=True)[:batch_size])
            
            # Delete the records with these IDs
            count, _ = PreplotLine.objects.filter(id__in=ids).delete()
            
            total_deleted += count
            self.stdout.write(self.style.SUCCESS(f'{total_deleted} PreplotLine records deleted so far.'))

        self.stdout.write(self.style.SUCCESS('All PreplotLine records deleted successfully.'))
