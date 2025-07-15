"""
AI Service for integrating crop disease detection with Django models
"""

import os
import sys
import logging
from typing import Dict, Optional
from django.conf import settings
from django.core.files.storage import default_storage
from dashboard.models import CropImage, DiagnosisResult, Disease, ModelTrainingLog
from datetime import datetime

# Add ai_models to Python path
sys.path.append(os.path.join(settings.BASE_DIR, 'ai_models'))

try:
    from crop_disease_model import CropDiseaseModel
except ImportError as e:
    print(f"Warning: Could not import AI model: {e}")
    CropDiseaseModel = None

logger = logging.getLogger(__name__)

class AIService:
    """
    Service class for AI model operations
    """
    
    def __init__(self):
        self.model = None
        self._load_active_model()
    
    def _load_active_model(self):
        """Load the currently active model"""
        try:
            # Get active model from database
            active_model_log = ModelTrainingLog.objects.filter(is_active=True).first()
            
            if active_model_log and CropDiseaseModel:
                model_path = active_model_log.model_file_path
                if os.path.exists(model_path):
                    self.model = CropDiseaseModel(model_path)
                    logger.info(f"Loaded active model: {active_model_log.version}")
                else:
                    logger.warning(f"Model file not found: {model_path}")
            else:
                logger.warning("No active model found in database")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
    
    def diagnose_crop_image(self, crop_image: CropImage) -> DiagnosisResult:
        """
        Diagnose a crop image and create diagnosis result
        
        Args:
            crop_image: CropImage instance
            
        Returns:
            DiagnosisResult instance
        """
        # Create initial diagnosis result
        diagnosis = DiagnosisResult.objects.create(
            crop_image=crop_image,
            status='processing',
            model_version=self.model.model_version if self.model else 'unknown',
            confidence_score=0.0,  # Initialize with 0, will be updated after diagnosis
            processing_time=0.0    # Initialize with 0, will be updated after diagnosis
        )
        
        try:
            if not self.model:
                raise Exception("No AI model available for diagnosis")
            
            # Get full path to image
            image_path = crop_image.image.path
            
            if not os.path.exists(image_path):
                raise Exception(f"Image file not found: {image_path}")
            
            # Run AI prediction
            logger.info(f"Starting diagnosis for image: {crop_image.original_filename}")
            prediction_result = self.model.predict(image_path)
            
            # Update diagnosis with results
            diagnosis.is_diseased = bool(prediction_result['is_diseased'])
            diagnosis.confidence_score = float(prediction_result['confidence_score'])
            diagnosis.severity = str(prediction_result['severity'])
            diagnosis.processing_time = float(prediction_result['processing_time'])
            diagnosis.alternative_diseases = self._sanitize_json_data(prediction_result['alternative_diseases'])
            diagnosis.model_version = str(prediction_result['model_version'])
            
            # Find or create disease entry
            if prediction_result['is_diseased']:
                disease_name = prediction_result['detected_disease']
                disease, created = Disease.objects.get_or_create(
                    name=disease_name,
                    defaults={
                        'description': f'AI detected disease: {disease_name}',
                        'symptoms': 'Detected by AI model',
                        'treatment': 'Consult agricultural expert',
                        'affected_crops': crop_image.crop_type or 'Various'
                    }
                )
                diagnosis.detected_disease = disease
                
                if created:
                    logger.info(f"Created new disease entry: {disease_name}")
            
            # Generate basic recommendations
            diagnosis.recommendations = self._sanitize_json_data(self._generate_recommendations(prediction_result))
            
            # Mark as completed
            diagnosis.status = 'completed'
            diagnosis.completed_at = datetime.now()
            
            # Update crop image processed timestamp
            crop_image.processed_at = datetime.now()
            crop_image.save()
            
            logger.info(f"Diagnosis completed: {prediction_result['detected_disease']} ({prediction_result['confidence_score']:.1f}%)")
            
        except Exception as e:
            # Mark diagnosis as failed
            diagnosis.status = 'failed'
            diagnosis.error_message = str(e)
            
            # Ensure required fields are set even on failure
            if diagnosis.confidence_score is None:
                diagnosis.confidence_score = 0.0
            if diagnosis.processing_time is None:
                diagnosis.processing_time = 0.0
                
            logger.error(f"Diagnosis failed: {str(e)}")
        
        finally:
            diagnosis.save()
        
        return diagnosis
    
    def _generate_recommendations(self, prediction_result: Dict) -> list:
        """
        Generate treatment recommendations based on diagnosis
        
        Args:
            prediction_result: AI prediction results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not prediction_result['is_diseased']:
            recommendations = [
                "Crop appears healthy",
                "Continue regular monitoring",
                "Maintain current care practices"
            ]
        else:
            disease = prediction_result['detected_disease']
            severity = prediction_result['severity']
            confidence = prediction_result['confidence_score']
            
            # Basic recommendations based on severity
            if severity == 'critical':
                recommendations = [
                    f"Immediate attention required for {disease}",
                    "Consult agricultural expert urgently",
                    "Consider quarantine measures",
                    "Apply appropriate fungicide/treatment"
                ]
            elif severity == 'high':
                recommendations = [
                    f"High risk {disease} detected",
                    "Consult agricultural expert soon",
                    "Monitor spread to other plants",
                    "Apply preventive measures"
                ]
            elif severity == 'medium':
                recommendations = [
                    f"Moderate {disease} symptoms detected",
                    "Regular monitoring recommended",
                    "Consider preventive treatment",
                    "Improve plant care conditions"
                ]
            else:  # low severity
                recommendations = [
                    f"Early stage {disease} detected",
                    "Monitor plant closely",
                    "Improve environmental conditions",
                    "Consider organic treatments"
                ]
            
            # Add confidence-based recommendations
            if confidence < 70:
                recommendations.append("Low confidence - consider getting a second opinion")
        
        return recommendations
    
    def get_model_info(self) -> Optional[Dict]:
        """
        Get information about the currently loaded model
        
        Returns:
            Dictionary with model information or None
        """
        if not self.model:
            return None
        
        active_model_log = ModelTrainingLog.objects.filter(is_active=True).first()
        
        return {
            'version': self.model.model_version,
            'class_names': self.model.class_names,
            'input_shape': self.model.input_shape,
            'training_accuracy': active_model_log.training_accuracy if active_model_log else None,
            'validation_accuracy': active_model_log.validation_accuracy if active_model_log else None,
            'dataset_size': active_model_log.dataset_size if active_model_log else None
        }
    
    def reload_model(self):
        """Reload the active model (useful after training new model)"""
        self._load_active_model()
    
    def _sanitize_json_data(self, data):
        """
        Sanitize data for JSON serialization, converting numpy types to Python types
        
        Args:
            data: Data to sanitize
            
        Returns:
            JSON-serializable data
        """
        import json
        import numpy as np
        
        if isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, (np.int64, np.int32, np.int16, np.int8)):
            return int(data)
        elif isinstance(data, (np.float64, np.float32, np.float16)):
            return float(data)
        elif isinstance(data, np.bool_):
            return bool(data)
        elif isinstance(data, dict):
            return {key: self._sanitize_json_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        else:
            return data

# Global AI service instance
ai_service = AIService()
