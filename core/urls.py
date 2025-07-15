from django.urls import path
from .views import landing_page, home_page

app_name = 'core'

urlpatterns = [
     path('', landing_page, name='landing'),
     path('home/', home_page, name='home'),
]