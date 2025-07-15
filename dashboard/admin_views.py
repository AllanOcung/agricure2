"""
Admin Dashboard Views for Model Management
"""

import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.conf import settings

from .models import (
    ModelTrainingLog, Disease, CropImage, DiagnosisResult, 
    TrainingImage, UserFeedback
)
from .ai_service import AIService
from .decorators import admin_required, role_required
import subprocess
import threading

# Try to import psutil, install if not available
try:
    import psutil
except ImportError:
    psutil = None

@admin_required
def admin_dashboard(request):
    """Main admin dashboard view"""
    
    # Get key metrics
    total_models = ModelTrainingLog.objects.count()
    active_models = ModelTrainingLog.objects.filter(is_active=True).count()
    total_diagnoses = DiagnosisResult.objects.count()
    total_images = CropImage.objects.count()
    
    # Recent activity
    recent_diagnoses = DiagnosisResult.objects.select_related(
        'crop_image__user', 'detected_disease'
    ).order_by('-created_at')[:10]
    
    recent_training = ModelTrainingLog.objects.order_by('-training_started_at')[:5]
    
    # Performance metrics
    accuracy_data = []
    for log in ModelTrainingLog.objects.filter(is_active=True):
        accuracy_data.append({
            'version': log.version,
            'training_accuracy': log.training_accuracy,
            'validation_accuracy': log.validation_accuracy,
            'date': log.training_started_at.strftime('%Y-%m-%d')
        })
    
    # Disease distribution
    disease_stats = Disease.objects.annotate(
        diagnosis_count=Count('diagnosisresult')
    ).order_by('-diagnosis_count')[:10]
    
    context = {
        'total_models': total_models,
        'active_models': active_models,
        'total_diagnoses': total_diagnoses,
        'total_images': total_images,
        'recent_diagnoses': recent_diagnoses,
        'recent_training': recent_training,
        'accuracy_data': accuracy_data,
        'disease_stats': disease_stats,
        'page_title': 'Admin Dashboard'
    }
    
    return render(request, 'dashboard/admin/dashboard.html', context)

@admin_required
def model_management(request):
    """Model management view"""
    
    models = ModelTrainingLog.objects.all().order_by('-training_started_at')
    
    # Add pagination
    paginator = Paginator(models, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get active model
    active_model = ModelTrainingLog.objects.filter(is_active=True).first()
    
    # Get available datasets
    dataset_path = os.path.join(settings.BASE_DIR, 'training_data')
    datasets = []
    if os.path.exists(dataset_path):
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                image_count = len([f for f in os.listdir(item_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                datasets.append({
                    'name': item,
                    'path': item_path,
                    'image_count': image_count
                })
    
    context = {
        'models': page_obj,
        'active_model': active_model,
        'datasets': datasets,
        'page_title': 'Model Management'
    }
    
    return render(request, 'dashboard/admin/model_management.html', context)

@admin_required
def model_performance(request, model_id):
    """Detailed model performance view"""
    
    model = get_object_or_404(ModelTrainingLog, id=model_id)
    
    # Get diagnoses made with this model
    diagnoses = DiagnosisResult.objects.filter(
        model_version=model.version
    ).select_related('crop_image__user', 'detected_disease')
    
    # Calculate performance metrics
    total_diagnoses = diagnoses.count()
    successful_diagnoses = diagnoses.filter(status='completed').count()
    failed_diagnoses = diagnoses.filter(status='failed').count()
    
    # Confidence distribution
    confidence_ranges = {
        'high': diagnoses.filter(confidence_score__gte=80).count(),
        'medium': diagnoses.filter(confidence_score__gte=60, confidence_score__lt=80).count(),
        'low': diagnoses.filter(confidence_score__lt=60).count()
    }
    
    # Disease detection frequency
    disease_frequency = diagnoses.values('detected_disease__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # User feedback if available
    feedback = UserFeedback.objects.filter(
        diagnosis__model_version=model.version
    ).aggregate(
        avg_accuracy=Count('id', filter=Q(feedback_type='accuracy')),
        avg_usefulness=Count('id', filter=Q(feedback_type='usefulness'))
    )
    
    context = {
        'model': model,
        'total_diagnoses': total_diagnoses,
        'successful_diagnoses': successful_diagnoses,
        'failed_diagnoses': failed_diagnoses,
        'confidence_ranges': confidence_ranges,
        'disease_frequency': disease_frequency,
        'feedback': feedback,
        'page_title': f'Model Performance - {model.version}'
    }
    
    return render(request, 'dashboard/admin/model_performance.html', context)

@admin_required
@require_http_methods(["POST"])
def activate_model(request, model_id):
    """Activate a specific model"""
    
    try:
        # Deactivate all models
        ModelTrainingLog.objects.update(is_active=False)
        
        # Activate the selected model
        model = get_object_or_404(ModelTrainingLog, id=model_id)
        model.is_active = True
        model.save()
        
        # Reload AI service with new model
        ai_service = AIService()
        ai_service._load_active_model()
        
        messages.success(request, f'Model {model.version} has been activated successfully!')
        
    except Exception as e:
        messages.error(request, f'Failed to activate model: {str(e)}')
    
    return redirect('dashboard:admin:model_management')

@admin_required
@require_http_methods(["POST"])
def deactivate_model(request, model_id):
    """Deactivate a specific model"""
    if request.method == 'POST':
        try:
            model = ModelTrainingLog.objects.get(id=model_id)
            model.is_active = False
            model.save()
            
            messages.success(request, f'Model {model.version} has been deactivated.')
        except ModelTrainingLog.DoesNotExist:
            messages.error(request, 'Model not found.')
        except Exception as e:
            messages.error(request, f'Error deactivating model: {str(e)}')
    
    return redirect('dashboard:admin:model_management')

@admin_required
@require_http_methods(["POST"])
def delete_model(request, model_id):
    """Delete a model and its files"""
    
    try:
        model = get_object_or_404(ModelTrainingLog, id=model_id)
        
        # Don't delete active model
        if model.is_active:
            messages.error(request, 'Cannot delete active model. Please activate another model first.')
            return redirect('dashboard:admin:model_management')
        
        # Delete model files
        if os.path.exists(model.model_file_path):
            import shutil
            shutil.rmtree(model.model_file_path)
        
        # Delete database record
        model_version = model.version
        model.delete()
        
        messages.success(request, f'Model {model_version} has been deleted successfully!')
        
    except Exception as e:
        messages.error(request, f'Failed to delete model: {str(e)}')
    
    return redirect('dashboard:admin:model_management')

@admin_required
def train_model(request):
    """Model training interface"""
    
    if request.method == 'POST':
        return handle_model_training(request)
    
    # Get available datasets
    dataset_path = os.path.join(settings.BASE_DIR, 'training_data')
    datasets = []
    if os.path.exists(dataset_path):
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                image_count = len([f for f in os.listdir(item_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                datasets.append({
                    'name': item,
                    'path': item_path,
                    'image_count': image_count
                })
    
    context = {
        'datasets': datasets,
        'page_title': 'Train New Model'
    }
    
    return render(request, 'dashboard/admin/train_model.html', context)

def handle_model_training(request):
    """Handle model training request"""
    
    try:
        dataset_path = request.POST.get('dataset_path', 'training_data')
        epochs = int(request.POST.get('epochs', 20))
        batch_size = int(request.POST.get('batch_size', 16))
        model_version = request.POST.get('model_version', '')
        
        # Validate inputs
        if not os.path.exists(dataset_path):
            messages.error(request, f'Dataset path does not exist: {dataset_path}')
            return redirect('dashboard:admin:train_model')
        
        if epochs < 1 or epochs > 200:
            messages.error(request, 'Epochs must be between 1 and 200')
            return redirect('dashboard:admin:train_model')
        
        if batch_size < 1 or batch_size > 128:
            messages.error(request, 'Batch size must be between 1 and 128')
            return redirect('dashboard:admin:train_model')
        
        # Start training in background
        def train_model_background():
            try:
                call_command(
                    'train_model',
                    dataset_path=dataset_path,
                    epochs=epochs,
                    batch_size=batch_size,
                    model_version=model_version
                )
            except Exception as e:
                print(f"Training error: {str(e)}")
        
        # Start training thread
        training_thread = threading.Thread(target=train_model_background)
        training_thread.start()
        
        messages.success(request, 'Model training started! You can monitor progress in the model management section.')
        
    except Exception as e:
        messages.error(request, f'Failed to start training: {str(e)}')
    
    return redirect('dashboard:admin:model_management')

@admin_required
def training_logs(request):
    """View training logs and status"""
    
    logs = ModelTrainingLog.objects.all().order_by('-training_started_at')
    
    # Add pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'logs': page_obj,
        'page_title': 'Training Logs'
    }
    
    return render(request, 'dashboard/admin/training_logs.html', context)

@admin_required
def dataset_management(request):
    """Dataset management view"""
    
    # Get training images by class
    dataset_stats = []
    training_images = TrainingImage.objects.select_related('disease').all()
    
    disease_counts = {}
    for image in training_images:
        disease_name = image.disease.name
        if disease_name not in disease_counts:
            disease_counts[disease_name] = 0
        disease_counts[disease_name] += 1
    
    for disease_name, count in disease_counts.items():
        dataset_stats.append({
            'disease': disease_name,
            'count': count
        })
    
    # Get file system dataset info
    dataset_path = os.path.join(settings.BASE_DIR, 'training_data')
    filesystem_stats = []
    if os.path.exists(dataset_path):
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path):
                image_count = len([f for f in os.listdir(item_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                filesystem_stats.append({
                    'name': item,
                    'count': image_count,
                    'path': item_path
                })
    
    context = {
        'dataset_stats': dataset_stats,
        'filesystem_stats': filesystem_stats,
        'page_title': 'Dataset Management'
    }
    
    return render(request, 'dashboard/admin/dataset_management.html', context)

@admin_required
def system_health(request):
    """System health and diagnostics"""
    
    # Check AI service status
    ai_service = AIService()
    ai_status = {
        'model_loaded': ai_service.model is not None,
        'model_version': ai_service.model.model_version if ai_service.model else 'None',
        'model_classes': len(ai_service.model.class_names) if ai_service.model else 0
    }
    
    # Check disk space
    import shutil
    disk_usage = shutil.disk_usage(settings.BASE_DIR)
    disk_info = {
        'total': disk_usage.total / (1024**3),  # GB
        'used': disk_usage.used / (1024**3),   # GB
        'free': disk_usage.free / (1024**3),   # GB
        'percent_used': (disk_usage.used / disk_usage.total) * 100
    }
    
    # Check database stats
    db_stats = {
        'total_users': CropImage.objects.values('user').distinct().count(),
        'total_images': CropImage.objects.count(),
        'total_diagnoses': DiagnosisResult.objects.count(),
        'failed_diagnoses': DiagnosisResult.objects.filter(status='failed').count(),
        'avg_processing_time': DiagnosisResult.objects.filter(
            status='completed'
        ).aggregate(avg_time=Count('processing_time'))['avg_time'] or 0
    }
    
    # Recent errors
    recent_errors = DiagnosisResult.objects.filter(
        status='failed'
    ).order_by('-created_at')[:10]
    
    context = {
        'ai_status': ai_status,
        'disk_info': disk_info,
        'db_stats': db_stats,
        'recent_errors': recent_errors,
        'page_title': 'System Health'
    }
    
    return render(request, 'dashboard/admin/system_health.html', context)

@admin_required
def get_training_status(request):
    """Get current training status via AJAX"""
    
    try:
        # Get the most recent training log
        recent_training = ModelTrainingLog.objects.order_by('-training_started_at').first()
        
        if not recent_training:
            return JsonResponse({'status': 'no_training'})
        
        # Check if training is still running
        if recent_training.training_completed_at is None:
            return JsonResponse({
                'status': 'training',
                'model_version': recent_training.version,
                'started_at': recent_training.training_started_at.isoformat(),
                'epochs': recent_training.epochs,
                'batch_size': recent_training.batch_size
            })
        else:
            return JsonResponse({
                'status': 'completed',
                'model_version': recent_training.version,
                'training_accuracy': recent_training.training_accuracy,
                'validation_accuracy': recent_training.validation_accuracy,
                'completed_at': recent_training.training_completed_at.isoformat()
            })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@admin_required
def training_progress(request):
    """Get training progress via AJAX"""
    try:
        # Get the most recent training log
        recent_training = ModelTrainingLog.objects.filter(
            training_completed_at__isnull=True
        ).order_by('-training_started_at').first()
        
        if not recent_training:
            return JsonResponse({'status': 'no_training'})
        
        # Calculate elapsed time
        elapsed = timezone.now() - recent_training.training_started_at
        elapsed_hours = elapsed.total_seconds() / 3600
        
        return JsonResponse({
            'status': 'training',
            'model_version': recent_training.version,
            'started_at': recent_training.training_started_at.isoformat(),
            'elapsed_hours': elapsed_hours,
            'epochs': recent_training.epochs,
            'batch_size': recent_training.batch_size
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@admin_required
def stop_training(request):
    """Stop current training session"""
    if request.method == 'POST':
        try:
            # Get the current training session
            current_training = ModelTrainingLog.objects.filter(
                training_completed_at__isnull=True
            ).order_by('-training_started_at').first()
            
            if current_training:
                # Mark as stopped
                current_training.training_completed_at = timezone.now()
                current_training.status = 'stopped'
                current_training.save()
                
                messages.success(request, 'Training session has been stopped.')
            else:
                messages.warning(request, 'No active training session found.')
                
        except Exception as e:
            messages.error(request, f'Error stopping training: {str(e)}')
    
    return redirect('dashboard:admin:training_logs')

@admin_required
def model_performance_detail(request, model_id):
    """Detailed performance view for a specific model"""
    try:
        model = ModelTrainingLog.objects.get(id=model_id)
        
        # Get training logs for this model
        training_logs = ModelTrainingLog.objects.filter(
            version=model.version
        ).order_by('-training_started_at')
        
        # Get diagnosis results for this model
        diagnosis_results = DiagnosisResult.objects.filter(
            model_version=model.version
        ).order_by('-created_at')[:100]
        
        # Calculate performance metrics
        performance_metrics = {
            'total_predictions': diagnosis_results.count(),
            'successful_predictions': diagnosis_results.filter(status='completed').count(),
            'failed_predictions': diagnosis_results.filter(status='failed').count(),
            'avg_confidence': diagnosis_results.aggregate(
                avg_conf=Avg('confidence_score')
            )['avg_conf'] or 0
        }
        
        context = {
            'model': model,
            'training_logs': training_logs,
            'diagnosis_results': diagnosis_results,
            'performance_metrics': performance_metrics,
            'page_title': f'Model Performance - {model.version}'
        }
        
        return render(request, 'dashboard/admin/model_performance_detail.html', context)
        
    except ModelTrainingLog.DoesNotExist:
        messages.error(request, 'Model not found.')
        return redirect('dashboard:admin:model_performance')

@admin_required
def training_log_detail(request, log_id):
    """Detailed view of a training log"""
    try:
        log = ModelTrainingLog.objects.get(id=log_id)
        
        context = {
            'log': log,
            'page_title': f'Training Log - {log.version}'
        }
        
        return render(request, 'dashboard/admin/training_log_detail.html', context)
        
    except ModelTrainingLog.DoesNotExist:
        messages.error(request, 'Training log not found.')
        return redirect('dashboard:admin:training_logs')

@admin_required
def upload_dataset(request):
    """Upload new images to dataset"""
    if request.method == 'POST':
        try:
            disease_class = request.POST.get('disease_class')
            new_class_name = request.POST.get('new_class_name')
            uploaded_files = request.FILES.getlist('images')
            
            # Determine the disease class
            if disease_class == 'new' and new_class_name:
                disease, created = Disease.objects.get_or_create(
                    name=new_class_name,
                    defaults={'description': f'Disease class: {new_class_name}'}
                )
            else:
                disease = Disease.objects.get(name=disease_class)
            
            # Process uploaded files
            uploaded_count = 0
            for uploaded_file in uploaded_files:
                # Save the training image
                training_image = TrainingImage.objects.create(
                    disease=disease,
                    image=uploaded_file,
                    source='upload'
                )
                uploaded_count += 1
            
            messages.success(request, f'Successfully uploaded {uploaded_count} images for {disease.name}.')
            
        except Exception as e:
            messages.error(request, f'Error uploading images: {str(e)}')
    
    return redirect('dashboard:admin:dataset_management')

@admin_required
def clean_dataset(request):
    """Clean corrupted images from dataset"""
    if request.method == 'POST':
        try:
            from PIL import Image
            
            cleaned_count = 0
            training_images = TrainingImage.objects.all()
            
            for training_image in training_images:
                try:
                    # Try to open the image
                    with Image.open(training_image.image.path) as img:
                        img.verify()
                except Exception:
                    # Image is corrupted, delete it
                    training_image.delete()
                    cleaned_count += 1
            
            messages.success(request, f'Successfully cleaned {cleaned_count} corrupted images.')
            
        except Exception as e:
            messages.error(request, f'Error cleaning dataset: {str(e)}')
    
    return redirect('dashboard:admin:dataset_management')

@admin_required
def validate_dataset(request):
    """Validate dataset integrity and balance"""
    if request.method == 'POST':
        try:
            # Get dataset statistics
            training_images = TrainingImage.objects.select_related('disease').all()
            disease_counts = {}
            
            for image in training_images:
                disease_name = image.disease.name
                if disease_name not in disease_counts:
                    disease_counts[disease_name] = 0
                disease_counts[disease_name] += 1
            
            total_images = sum(disease_counts.values())
            
            # Calculate balance score
            if len(disease_counts) > 1:
                max_count = max(disease_counts.values())
                min_count = min(disease_counts.values())
                balance_score = (min_count / max_count) * 100
            else:
                balance_score = 100
            
            # Validation results
            validation_results = {
                'total_images': total_images,
                'total_classes': len(disease_counts),
                'class_distribution': disease_counts,
                'balance_score': balance_score,
                'is_balanced': balance_score >= 70,
                'recommendations': []
            }
            
            if balance_score < 70:
                validation_results['recommendations'].append(
                    'Dataset is imbalanced. Consider adding more images to underrepresented classes.'
                )
            
            if total_images < 1000:
                validation_results['recommendations'].append(
                    'Dataset is small. Consider adding more images for better model performance.'
                )
            
            messages.success(request, f'Dataset validation completed. Balance score: {balance_score:.1f}%')
            
        except Exception as e:
            messages.error(request, f'Error validating dataset: {str(e)}')
    
    return redirect('dashboard:admin:dataset_management')

@admin_required
def health_check(request):
    """Run system health checks"""
    if request.method == 'POST':
        try:
            # Run various health checks
            checks = {
                'ai_service': check_ai_service(),
                'database': check_database(),
                'disk_space': check_disk_space(),
                'model_files': check_model_files()
            }
            
            # Return results
            return JsonResponse({
                'success': True,
                'checks': checks,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

# API Endpoints
@admin_required
def api_stats(request):
    """API endpoint for dashboard statistics"""
    try:
        stats = {
            'total_models': ModelTrainingLog.objects.count(),
            'active_models': ModelTrainingLog.objects.filter(is_active=True).count(),
            'total_diagnoses': DiagnosisResult.objects.count(),
            'recent_diagnoses': DiagnosisResult.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'total_users': CropImage.objects.values('user').distinct().count(),
            'dataset_size': TrainingImage.objects.count()
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
def api_models(request):
    """API endpoint for model information"""
    try:
        models = ModelTrainingLog.objects.all().values(
            'id', 'version', 'validation_accuracy', 'is_active', 'training_started_at'
        )
        
        return JsonResponse({'models': list(models)})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
def api_training_status(request):
    """API endpoint for training status"""
    try:
        # Get current training session
        current_training = ModelTrainingLog.objects.filter(
            training_completed_at__isnull=True
        ).order_by('-training_started_at').first()
        
        if current_training:
            elapsed = timezone.now() - current_training.training_started_at
            return JsonResponse({
                'status': 'training',
                'session_id': current_training.id,
                'model_version': current_training.version,
                'elapsed_seconds': elapsed.total_seconds(),
                'epochs': current_training.epochs
            })
        else:
            return JsonResponse({'status': 'idle'})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
def api_system_metrics(request):
    """API endpoint for system metrics"""
    try:
        # Use basic system info if psutil is not available
        if psutil:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'disk_usage': disk.percent,
                'timestamp': timezone.now().isoformat()
            }
        else:
            # Fallback metrics
            import shutil
            disk_usage = shutil.disk_usage(settings.BASE_DIR)
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            metrics = {
                'cpu_usage': 0,  # Not available without psutil
                'memory_usage': 0,  # Not available without psutil
                'disk_usage': disk_percent,
                'timestamp': timezone.now().isoformat()
            }
        
        return JsonResponse(metrics)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Helper functions
def check_ai_service():
    """Check AI service health"""
    try:
        ai_service = AIService()
        return {
            'status': 'healthy' if ai_service.model else 'unhealthy',
            'model_loaded': ai_service.model is not None,
            'details': 'AI service is running' if ai_service.model else 'No model loaded'
        }
    except Exception as e:
        return {
            'status': 'error',
            'model_loaded': False,
            'details': str(e)
        }

def check_database():
    """Check database health"""
    try:
        # Try a simple query
        ModelTrainingLog.objects.count()
        return {
            'status': 'healthy',
            'details': 'Database is accessible'
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e)
        }

def check_disk_space():
    """Check disk space"""
    try:
        import shutil
        disk_usage = shutil.disk_usage(settings.BASE_DIR)
        percent_used = (disk_usage.used / disk_usage.total) * 100
        
        status = 'healthy' if percent_used < 85 else 'warning' if percent_used < 95 else 'error'
        
        return {
            'status': status,
            'percent_used': percent_used,
            'details': f'Disk usage: {percent_used:.1f}%'
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e)
        }

def check_model_files():
    """Check model files integrity"""
    try:
        models = ModelTrainingLog.objects.all()
        missing_files = []
        
        for model in models:
            if model.model_file_path and not os.path.exists(model.model_file_path):
                missing_files.append(model.version)
        
        if missing_files:
            return {
                'status': 'warning',
                'details': f'Missing model files: {", ".join(missing_files)}'
            }
        else:
            return {
                'status': 'healthy',
                'details': 'All model files present'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e)
        }
