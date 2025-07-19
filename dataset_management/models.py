from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import os


class Dataset(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('training', 'Training Dataset'),
        ('validation', 'Validation Dataset'),
        ('test', 'Test Dataset'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    dataset_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='training')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # File upload
    zip_file = models.FileField(
        upload_to='datasets/uploads/',
        validators=[FileExtensionValidator(allowed_extensions=['zip'])],
        help_text='Upload a ZIP file containing organized image folders'
    )
    
    # Metadata
    total_images = models.PositiveIntegerField(default=0)
    total_classes = models.PositiveIntegerField(default=0)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    
    # Processing info
    processing_log = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # User tracking
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_datasets')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'
    
    def __str__(self):
        return f"{self.name} ({self.dataset_type})"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def get_status_display_class(self):
        """Return CSS class for status display"""
        status_classes = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'failed': 'danger',
        }
        return status_classes.get(self.status, 'secondary')
    
    def get_organized_path(self):
        """Return the organized dataset path for training"""
        from django.conf import settings
        dataset_folder_name = f"dataset_{self.id:03d}_{self.name.lower().replace(' ', '_')}_v1"
        return os.path.join(settings.MEDIA_ROOT, 'datasets', dataset_folder_name)
    
    def get_organized_url(self):
        """Return the organized dataset URL"""
        from django.conf import settings
        dataset_folder_name = f"dataset_{self.id:03d}_{self.name.lower().replace(' ', '_')}_v1"
        return f"{settings.MEDIA_URL}datasets/{dataset_folder_name}/"
    
    def is_ready_for_training(self):
        """Check if dataset is ready for training"""
        return self.status == 'completed' and self.total_images > 0 and self.total_classes > 1
    
    def get_keras_directory_structure(self):
        """Return information about the Keras-ready directory structure"""
        if not self.is_ready_for_training():
            return None
        
        organized_path = self.get_organized_path()
        structure = {}
        
        if os.path.exists(organized_path):
            for class_name in os.listdir(organized_path):
                class_path = os.path.join(organized_path, class_name)
                if os.path.isdir(class_path):
                    image_count = len([f for f in os.listdir(class_path) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
                    structure[class_name] = {
                        'path': class_path,
                        'image_count': image_count
                    }
        
        return structure


class DatasetImage(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='datasets/images/')
    original_filename = models.CharField(max_length=255)
    class_name = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField(default=0)
    image_width = models.PositiveIntegerField(default=0)
    image_height = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['class_name', 'original_filename']
        verbose_name = 'Dataset Image'
        verbose_name_plural = 'Dataset Images'
    
    def __str__(self):
        return f"{self.original_filename} ({self.class_name})"


class DatasetClass(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='classes')
    class_name = models.CharField(max_length=100)
    image_count = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['class_name']
        verbose_name = 'Dataset Class'
        verbose_name_plural = 'Dataset Classes'
        unique_together = ['dataset', 'class_name']
    
    def __str__(self):
        return f"{self.class_name} ({self.image_count} images)"
