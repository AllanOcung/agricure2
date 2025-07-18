from django.urls import path, include
from . import views, admin_views, user_views, dataset_views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='home'),
    
    # User-facing views
    path('upload/', user_views.upload_image, name='upload_image'),
    path('diagnoses/', user_views.my_diagnoses, name='my_diagnoses'),
    path('diagnosis/<int:diagnosis_id>/', user_views.diagnosis_result, name='diagnosis_result'),
    path('compare/', user_views.model_comparison, name='model_comparison'),
    path('comparison/<int:crop_image_id>/', user_views.comparison_result, name='comparison_result'),
    path('models/', user_views.available_models, name='available_models'),
    path('model/<int:model_id>/', user_views.model_info, name='model_info'),
    path('profile/', views.profile_view, name='profile'),
    path('history/', views.diagnosis_history, name='history'),
    path('diagnosis/<int:diagnosis_id>/', views.diagnosis_detail, name='diagnosis_detail'),
    
]