"""
Django management command to train crop disease detection model
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dashboard.models import ModelTrainingLog, Disease
from datetime import datetime

# Add ai_models to Python path
ai_models_path = os.path.join(settings.BASE_DIR, 'ai_models')
if ai_models_path not in sys.path:
    sys.path.insert(0, ai_models_path)

try:
    from crop_disease_model import train_model, CropDiseaseModel
except ImportError as e:
    try:
        # Alternative import method
        from ai_models.crop_disease_model import train_model, CropDiseaseModel
    except ImportError as e2:
        print(f"Warning: Could not import AI model: {e}, {e2}")
        train_model = None
        CropDiseaseModel = None

class Command(BaseCommand):
    help = 'Train crop disease detection model with your dataset'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset-path',
            type=str,
            required=True,
            help='Path to the training dataset directory'
        )
        parser.add_argument(
            '--epochs',
            type=int,
            default=20,
            help='Number of training epochs (default: 20)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=32,
            help='Training batch size (default: 32)'
        )
        parser.add_argument(
            '--model-version',
            type=str,
            default=None,
            help='Model version name (default: auto-generated)'
        )

    def handle(self, *args, **options):
        # Check if AI model is available
        if train_model is None:
            raise CommandError('AI model not available. Please check the crop_disease_model module.')
        
        dataset_path = options['dataset_path']
        epochs = options['epochs']
        batch_size = options['batch_size']
        model_version = options['model_version']

        # Validate dataset path
        if not os.path.exists(dataset_path):
            raise CommandError(f'Dataset path does not exist: {dataset_path}')

        # Generate model version if not provided
        if not model_version:
            model_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Set model save path
        model_save_path = os.path.join(settings.BASE_DIR, 'ai_models', 'trained_models', model_version)
        os.makedirs(model_save_path, exist_ok=True)

        self.stdout.write(
            self.style.SUCCESS(f'Starting model training...')
        )
        self.stdout.write(f'Dataset path: {dataset_path}')
        self.stdout.write(f'Epochs: {epochs}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write(f'Model version: {model_version}')
        self.stdout.write(f'Save path: {model_save_path}')

        try:
            # Create training log entry
            training_log = ModelTrainingLog.objects.create(
                version=model_version,
                dataset_size=0,  # Will be updated after training
                training_accuracy=0.0,
                validation_accuracy=0.0,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=0.001,
                model_architecture='MobileNetV2',
                model_file_path=model_save_path,
                training_started_at=datetime.now()
            )

            self.stdout.write('Training log created in database...')

            # Train the model
            results = train_model(
                dataset_path=dataset_path,
                model_save_path=model_save_path,
                epochs=epochs,
                batch_size=batch_size
            )

            # Update training log with results
            training_log.dataset_size = results['dataset_size']
            training_log.training_accuracy = results['training_accuracy']
            training_log.validation_accuracy = results['validation_accuracy']
            training_log.training_completed_at = datetime.now()
            training_log.training_duration = results['training_duration']
            training_log.is_active = True  # Mark as active model
            training_log.save()

            # Deactivate previous models
            ModelTrainingLog.objects.filter(is_active=True).exclude(id=training_log.id).update(is_active=False)

            # Create or update disease entries
            self._update_diseases(results['class_names'])

            self.stdout.write(
                self.style.SUCCESS(
                    f'Model training completed successfully!\n'
                    f'Training accuracy: {results["training_accuracy"]:.4f}\n'
                    f'Validation accuracy: {results["validation_accuracy"]:.4f}\n'
                    f'Training duration: {results["training_duration"]}\n'
                    f'Model saved to: {model_save_path}'
                )
            )

        except Exception as e:
            # Update training log with error
            if 'training_log' in locals():
                training_log.error_message = str(e)
                training_log.save()
            
            raise CommandError(f'Training failed: {str(e)}')

    def _update_diseases(self, class_names):
        """Create or update disease entries in database"""
        self.stdout.write('Updating disease database...')
        
        for class_name in class_names:
            disease, created = Disease.objects.get_or_create(
                name=class_name,
                defaults={
                    'description': f'AI detected disease: {class_name}',
                    'symptoms': 'To be updated with expert knowledge',
                    'treatment': 'Consult agricultural expert for treatment',
                    'affected_crops': 'Various crops'
                }
            )
            
            if created:
                self.stdout.write(f'Created disease entry: {class_name}')
            else:
                self.stdout.write(f'Disease entry exists: {class_name}')
