from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='home'),
    # Image upload for diagnosis
    path('upload/', views.upload_image, name='upload_image'),
    # Diagnosis history
    path('my-diagnoses/', views.my_diagnoses, name='my_diagnoses'),
    # User profile
    path('profile/', views.profile, name='profile'),
]