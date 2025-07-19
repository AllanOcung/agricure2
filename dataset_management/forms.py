from django import forms
from .models import Dataset
from django.core.validators import FileExtensionValidator


class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'description', 'dataset_type', 'zip_file']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter dataset name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the dataset content and purpose...'
            }),
            'dataset_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'zip_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.zip',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = 'Give your dataset a descriptive name'
        self.fields['description'].help_text = 'Optional: Describe what this dataset contains'
        self.fields['dataset_type'].help_text = 'Select the purpose of this dataset'
        self.fields['zip_file'].help_text = '''
            Upload a ZIP file with the following structure:
            dataset.zip/
            ├── class1/
            │   ├── image1.jpg
            │   └── image2.jpg
            └── class2/
                ├── image3.jpg
                └── image4.jpg
        '''
    
    def clean_zip_file(self):
        zip_file = self.cleaned_data.get('zip_file')
        
        if zip_file:
            # Check file size (max 500MB)
            if zip_file.size > 500 * 1024 * 1024:
                raise forms.ValidationError('File too large. Maximum size is 500MB.')
            
            # Check file extension
            if not zip_file.name.lower().endswith('.zip'):
                raise forms.ValidationError('Please upload a ZIP file.')
        
        return zip_file
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        if name:
            # Check for duplicate names
            if Dataset.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError('A dataset with this name already exists.')
        
        return name


class DatasetFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Statuses')] + Dataset.STATUS_CHOICES
    TYPE_CHOICES = [('', 'All Types')] + Dataset.TYPE_CHOICES
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search datasets...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    dataset_type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
