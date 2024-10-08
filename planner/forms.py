from django import forms
from .models import File

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        filename = csv_file.name.split('.')[0]  # Get filename without extension

        if File.objects.filter(name=filename).exists():
            raise forms.ValidationError(f"A file with the name '{filename}' already exists.")

        return csv_file