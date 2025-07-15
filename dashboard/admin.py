from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Disease, TrainingImage, CropImage, DiagnosisResult, 
    ModelTrainingLog, UserFeedback
)

@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'scientific_name', 'affected_crops', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'scientific_name', 'affected_crops')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TrainingImage)
class TrainingImageAdmin(admin.ModelAdmin):
    list_display = ('disease', 'crop_type', 'severity', 'is_validated', 'uploaded_at')
    list_filter = ('disease', 'crop_type', 'severity', 'is_validated', 'uploaded_at')
    search_fields = ('disease__name', 'crop_type', 'notes')
    readonly_fields = ('uploaded_at',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

@admin.register(CropImage)
class CropImageAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_filename', 'crop_type', 'uploaded_at', 'processed_at')
    list_filter = ('crop_type', 'uploaded_at', 'processed_at')
    search_fields = ('user__email', 'original_filename', 'crop_type', 'location')
    readonly_fields = ('uploaded_at', 'file_size', 'image_width', 'image_height')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"

@admin.register(DiagnosisResult)
class DiagnosisResultAdmin(admin.ModelAdmin):
    list_display = ('crop_image_user', 'detected_disease', 'confidence_score', 'severity', 'status', 'created_at')
    list_filter = ('is_diseased', 'detected_disease', 'severity', 'status', 'model_version', 'created_at')
    search_fields = ('crop_image__user__email', 'detected_disease__name')
    readonly_fields = ('created_at', 'completed_at', 'processing_time')
    
    def crop_image_user(self, obj):
        return obj.crop_image.user.email
    crop_image_user.short_description = "User"
    
    def confidence_percentage(self, obj):
        return f"{obj.confidence_score:.1f}%"
    confidence_percentage.short_description = "Confidence"

@admin.register(ModelTrainingLog)
class ModelTrainingLogAdmin(admin.ModelAdmin):
    list_display = ('version', 'validation_accuracy', 'dataset_size', 'is_active', 'training_completed_at')
    list_filter = ('is_active', 'model_architecture', 'training_started_at')
    search_fields = ('version', 'model_architecture')
    readonly_fields = ('training_duration',)
    
    def accuracy_display(self, obj):
        return f"Train: {obj.training_accuracy:.2f}% | Val: {obj.validation_accuracy:.2f}%"
    accuracy_display.short_description = "Accuracy"

@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'diagnosis_disease', 'feedback_type', 'actual_disease', 'created_at')
    list_filter = ('feedback_type', 'created_at')
    search_fields = ('user__email', 'diagnosis__detected_disease__name', 'actual_disease__name')
    readonly_fields = ('created_at',)
    
    def diagnosis_disease(self, obj):
        return obj.diagnosis.detected_disease.name if obj.diagnosis.detected_disease else "Healthy"
    diagnosis_disease.short_description = "Diagnosed Disease"
