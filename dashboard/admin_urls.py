from django.urls import path
from . import admin_views

app_name = 'admin'

urlpatterns = [
    # Admin Dashboard
    path('', admin_views.admin_dashboard, name='dashboard'),
    
    # Model Management
    path('models/', admin_views.model_management, name='model_management'),
    path('models/activate/<int:model_id>/', admin_views.activate_model, name='activate_model'),
    path('models/deactivate/<int:model_id>/', admin_views.deactivate_model, name='deactivate_model'),
    path('models/delete/<int:model_id>/', admin_views.delete_model, name='delete_model'),
    
    # Model Training
    path('train/', admin_views.train_model, name='train_model'),
    path('train/progress/', admin_views.training_progress, name='training_progress'),
    path('train/stop/', admin_views.stop_training, name='stop_training'),
    
    # Model Performance
    path('performance/<int:model_id>', admin_views.model_performance, name='model_performance'),
    path('performance/<int:model_id>/', admin_views.model_performance_detail, name='model_performance_detail'),
    
    # Training Logs
    path('logs/', admin_views.training_logs, name='training_logs'),
    path('logs/<int:log_id>/', admin_views.training_log_detail, name='training_log_detail'),
    
    # Dataset Management
    path('datasets/', admin_views.dataset_management, name='dataset_management'),
    path('datasets/upload/', admin_views.upload_dataset, name='upload_dataset'),
    path('datasets/clean/', admin_views.clean_dataset, name='clean_dataset'),
    path('datasets/validate/', admin_views.validate_dataset, name='validate_dataset'),
    
    # System Health
    path('health/', admin_views.system_health, name='system_health'),
    path('health/check/', admin_views.health_check, name='health_check'),
    
    # API Endpoints
    path('api/stats/', admin_views.api_stats, name='api_stats'),
    path('api/models/', admin_views.api_models, name='api_models'),
    path('api/training-status/', admin_views.api_training_status, name='api_training_status'),
    path('api/system-metrics/', admin_views.api_system_metrics, name='api_system_metrics'),
]
