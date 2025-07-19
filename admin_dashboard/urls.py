from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Admin dashboard main pages
    path('', views.admin_dashboard_home, name='home'),
    
    
]
