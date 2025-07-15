from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os

User = get_user_model()

def upload_to_images(instance, filename):
    """Generate upload path for crop images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('crop_images', filename)

def upload_to_training(instance, filename):
    """Generate upload path for training images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('training_data', instance.disease.name, filename)

class Disease(models.Model):
    """Model to store information about different crop diseases"""
    name = models.CharField(max_length=100, unique=True)
    scientific_name = models.CharField(max_length=150, blank=True)
    description = models.TextField()
    symptoms = models.TextField()
    treatment = models.TextField()
    prevention = models.TextField(blank=True)
    affected_crops = models.TextField(help_text="Comma-separated list of crops")
    severity_levels = models.JSONField(default=dict, help_text="Severity level descriptions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class TrainingImage(models.Model):
    """Model to store training dataset images"""
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name='training_images')
    image = models.ImageField(upload_to=upload_to_training)
    crop_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ])
    is_validated = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.disease.name} - {self.crop_type} ({self.severity})"

class CropImage(models.Model):
    """Model to store user uploaded crop images for diagnosis"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crop_images')
    image = models.ImageField(upload_to=upload_to_images)
    crop_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Image metadata
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    image_width = models.PositiveIntegerField(null=True)
    image_height = models.PositiveIntegerField(null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.original_filename}"

class DiagnosisResult(models.Model):
    """Model to store AI diagnosis results"""
    SEVERITY_CHOICES = [
        ('healthy', 'Healthy'),
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical')
    ]
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    crop_image = models.OneToOneField(CropImage, on_delete=models.CASCADE, related_name='diagnosis')
    
    # AI Results
    is_diseased = models.BooleanField(default=False)
    detected_disease = models.ForeignKey(Disease, on_delete=models.SET_NULL, null=True, blank=True)
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Confidence percentage (0-100)"
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='healthy')
    
    # Model Information
    model_version = models.CharField(max_length=50, default='v1.0')
    processing_time = models.FloatField(help_text="Processing time in seconds")
    
    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional AI outputs
    alternative_diseases = models.JSONField(default=list, help_text="Other possible diseases with scores")
    region_analysis = models.JSONField(default=dict, help_text="Affected regions in the image")
    recommendations = models.JSONField(default=list, help_text="Treatment recommendations")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        disease_name = self.detected_disease.name if self.detected_disease else "Healthy"
        return f"{self.crop_image.user.email} - {disease_name} ({self.confidence_score:.1f}%)"

class ModelTrainingLog(models.Model):
    """Model to track model training sessions"""
    version = models.CharField(max_length=50, unique=True)
    dataset_size = models.PositiveIntegerField()
    training_accuracy = models.FloatField()
    validation_accuracy = models.FloatField()
    test_accuracy = models.FloatField(null=True, blank=True)
    
    # Training parameters
    epochs = models.PositiveIntegerField()
    batch_size = models.PositiveIntegerField()
    learning_rate = models.FloatField()
    model_architecture = models.CharField(max_length=100)
    
    # Files
    model_file_path = models.CharField(max_length=500)
    weights_file_path = models.CharField(max_length=500, blank=True)
    training_log_file = models.CharField(max_length=500, blank=True)
    
    # Status
    is_active = models.BooleanField(default=False)
    training_started_at = models.DateTimeField()
    training_completed_at = models.DateTimeField(null=True, blank=True)
    training_duration = models.DurationField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-training_started_at']
    
    def __str__(self):
        return f"Model {self.version} - {self.validation_accuracy:.2f}% accuracy"

class UserFeedback(models.Model):
    """Model to collect user feedback on diagnosis results"""
    FEEDBACK_CHOICES = [
        ('correct', 'Diagnosis was correct'),
        ('incorrect', 'Diagnosis was incorrect'),
        ('partially_correct', 'Partially correct'),
        ('unsure', 'Not sure')
    ]
    
    diagnosis = models.OneToOneField(DiagnosisResult, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_CHOICES)
    actual_disease = models.ForeignKey(Disease, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="What the disease actually was")
    comments = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback for {self.diagnosis} - {self.feedback_type}"
