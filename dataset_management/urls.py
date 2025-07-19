from django.urls import path
from . import views

app_name = 'dataset_management'

urlpatterns = [
    # Dataset list and management
    path('', views.dataset_list, name='dataset_list'),
    path('upload/', views.dataset_upload, name='dataset_upload'),
    path('<int:pk>/', views.dataset_detail, name='dataset_detail'),
    path('<int:pk>/delete/', views.dataset_delete, name='dataset_delete'),
    path('<int:pk>/reprocess/', views.dataset_reprocess, name='dataset_reprocess'),
    path('<int:pk>/images/', views.dataset_images, name='dataset_images'),
    path('<int:pk>/training-info/', views.dataset_training_info, name='dataset_training_info'),
    path('<int:pk>/validate/', views.dataset_validate, name='dataset_validate'),
    path('<int:pk>/cleaning/', views.dataset_cleaning, name='dataset_cleaning'),
    path('<int:pk>/cleaning/delete-image/', views.delete_image, name='delete_image'),
    path('<int:pk>/cleaning/rename-class/', views.rename_class, name='rename_class'),
]
