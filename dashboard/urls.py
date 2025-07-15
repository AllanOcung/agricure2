from django.urls import path, include
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('profile/', views.profile_view, name='profile'),
    path('history/', views.diagnosis_history, name='history'),
    path('upload/', views.upload_image, name='upload'),
    path('diagnosis/<int:diagnosis_id>/', views.diagnosis_detail, name='diagnosis_detail'),
    
    # Admin URLs
    path('admin/', include('dashboard.admin_urls')),
]
