from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import zipfile
import os
import threading
import logging
from PIL import Image
from .models import Dataset, DatasetImage, DatasetClass
from .forms import DatasetUploadForm, DatasetFilterForm
from .services import process_dataset_upload
from dashboard.decorators import admin_required, role_required

logger = logging.getLogger('dataset_management')


@login_required
@role_required(['admin'])
def dataset_list(request):
    """List all datasets with filtering and pagination"""
    
    filter_form = DatasetFilterForm(request.GET)
    datasets = Dataset.objects.all()
    
    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        status = filter_form.cleaned_data.get('status')
        dataset_type = filter_form.cleaned_data.get('dataset_type')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if search:
            datasets = datasets.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        if status:
            datasets = datasets.filter(status=status)
        
        if dataset_type:
            datasets = datasets.filter(dataset_type=dataset_type)
        
        if date_from:
            datasets = datasets.filter(created_at__date__gte=date_from)
        
        if date_to:
            datasets = datasets.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(datasets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total_datasets': Dataset.objects.count(),
        'pending_datasets': Dataset.objects.filter(status='pending').count(),
        'processing_datasets': Dataset.objects.filter(status='processing').count(),
        'completed_datasets': Dataset.objects.filter(status='completed').count(),
        'failed_datasets': Dataset.objects.filter(status='failed').count(),
    }
    
    context = {
        'datasets': page_obj,
        'filter_form': filter_form,
        'stats': stats,
        'page_title': 'Dataset Management'
    }
    
    return render(request, 'dataset_management/dataset_list.html', context)


@login_required
@role_required(['admin'])
def dataset_upload(request):
    """Upload new dataset"""
    
    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                dataset = form.save(commit=False)
                dataset.uploaded_by = request.user
                dataset.file_size = request.FILES['zip_file'].size
                dataset.save()
                
                # Process the dataset asynchronously
                try:
                    process_dataset_upload(dataset.id)
                    messages.success(request, f'Dataset "{dataset.name}" uploaded successfully and is being processed.')
                except Exception as e:
                    logger.error(f'Error processing dataset {dataset.id}: {str(e)}')
                    dataset.status = 'failed'
                    dataset.error_message = str(e)
                    dataset.save()
                    messages.error(request, f'Dataset uploaded but processing failed: {str(e)}')
                
                return redirect('dataset_management:dataset_detail', pk=dataset.pk)
                
            except Exception as e:
                logger.error(f'Error uploading dataset: {str(e)}')
                messages.error(request, f'Error uploading dataset: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DatasetUploadForm()
    
    context = {
        'form': form,
        'page_title': 'Upload Dataset'
    }
    
    return render(request, 'dataset_management/dataset_upload.html', context)


@login_required
@role_required(['admin'])
def dataset_detail(request, pk):
    """View dataset details"""
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Get dataset classes and images
    classes = dataset.classes.all().order_by('class_name')
    images = dataset.images.all()[:20]  # Show first 20 images
    
    # Statistics
    stats = {
        'total_images': dataset.total_images,
        'total_classes': dataset.total_classes,
        'file_size_mb': dataset.file_size_mb,
        'avg_images_per_class': round(dataset.total_images / dataset.total_classes, 2) if dataset.total_classes > 0 else 0
    }
    
    context = {
        'dataset': dataset,
        'classes': classes,
        'images': images,
        'stats': stats,
        'page_title': f'Dataset: {dataset.name}'
    }
    
    return render(request, 'dataset_management/dataset_detail.html', context)


@login_required
@role_required(['admin'])
def dataset_delete(request, pk):
    """Delete dataset"""
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if request.method == 'POST':
        try:
            dataset_name = dataset.name
            
            # Delete associated files
            if dataset.zip_file:
                if os.path.exists(dataset.zip_file.path):
                    os.remove(dataset.zip_file.path)
            
            # Delete dataset images
            for image in dataset.images.all():
                if image.image and os.path.exists(image.image.path):
                    os.remove(image.image.path)
            
            dataset.delete()
            messages.success(request, f'Dataset "{dataset_name}" has been deleted successfully.')
            
        except Exception as e:
            logger.error(f'Error deleting dataset {pk}: {str(e)}')
            messages.error(request, f'Error deleting dataset: {str(e)}')
    
    return redirect('dataset_management:dataset_list')


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@role_required(['admin'])
def dataset_reprocess(request, pk):
    """Reprocess a failed dataset"""
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if dataset.status not in ['failed', 'pending']:
        return JsonResponse({
            'success': False,
            'error': 'Dataset can only be reprocessed if it failed or is pending.'
        })
    
    try:
        # Reset dataset status
        dataset.status = 'pending'
        dataset.error_message = ''
        dataset.processing_log = ''
        dataset.save()
        
        # Clear existing processed data
        dataset.images.all().delete()
        dataset.classes.all().delete()
        
        # Reprocess
        process_dataset_upload(dataset.id)
        
        return JsonResponse({
            'success': True,
            'message': 'Dataset is being reprocessed.'
        })
        
    except Exception as e:
        logger.error(f'Error reprocessing dataset {pk}: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@role_required(['admin'])
def dataset_images(request, pk):
    """View dataset images with pagination"""
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Filter by class if specified
    class_filter = request.GET.get('class')
    images = dataset.images.all()
    
    if class_filter:
        images = images.filter(class_name=class_filter)
    
    # Pagination
    paginator = Paginator(images, 50)  # 50 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all classes for filter dropdown
    classes = dataset.classes.all().order_by('class_name')
    
    context = {
        'dataset': dataset,
        'images': page_obj,
        'classes': classes,
        'current_class': class_filter,
        'page_title': f'Images: {dataset.name}'
    }
    
    return render(request, 'dataset_management/dataset_images.html', context)


@login_required
@role_required(['admin'])
def dataset_training_info(request, pk):
    """Get dataset training information as JSON"""
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if not dataset.is_ready_for_training():
        return JsonResponse({
            'success': False,
            'error': 'Dataset is not ready for training',
            'status': dataset.status,
            'total_images': dataset.total_images,
            'total_classes': dataset.total_classes
        })
    
    # Get organized directory structure
    structure = dataset.get_keras_directory_structure()
    
    training_info = {
        'success': True,
        'dataset_id': dataset.id,
        'dataset_name': dataset.name,
        'dataset_path': dataset.get_organized_path(),
        'dataset_url': dataset.get_organized_url(),
        'total_images': dataset.total_images,
        'total_classes': dataset.total_classes,
        'classes': structure,
        'keras_example': {
            'code': f'''
# Example usage with Keras ImageDataGenerator
from tensorflow.keras.preprocessing.image import ImageDataGenerator

dataset_path = "{dataset.get_organized_path()}"

# Create data generators
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    validation_split=0.2
)

# Training generator
train_generator = train_datagen.flow_from_directory(
    dataset_path,
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='training'
)

# Validation generator
validation_generator = train_datagen.flow_from_directory(
    dataset_path,
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='validation'
)
''',
            'pytorch_code': f'''
# Example usage with PyTorch
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

dataset_path = "{dataset.get_organized_path()}"

# Define transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# Create dataset
dataset = datasets.ImageFolder(dataset_path, transform=transform)

# Create data loader
data_loader = DataLoader(dataset, batch_size=32, shuffle=True)
'''
        }
    }
    
    return JsonResponse(training_info)


@login_required
@admin_required
def dataset_validate(request, pk):
    """
    Validate dataset for quality and training readiness
    """
    import os
    from PIL import Image
    
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if dataset.status != 'completed':
        messages.error(request, 'Dataset must be completed before validation.')
        return redirect('dataset_management:dataset_detail', pk=pk)
    
    validation_results = {
        'total_images': 0,
        'corrupted_images': [],
        'small_images': [],
        'large_images': [],
        'class_distribution': {},
        'recommendations': [],
        'is_training_ready': True
    }
    
    # Get dataset images
    images = DatasetImage.objects.filter(dataset=dataset)
    validation_results['total_images'] = images.count()
    
    # Validate each image
    for image in images:
        try:
            # Check if image file exists
            if not os.path.exists(image.image.path):
                validation_results['corrupted_images'].append({
                    'filename': image.original_filename,
                    'reason': 'File not found'
                })
                continue
                
            # Try to open and validate image
            with Image.open(image.image.path) as img:
                width, height = img.size
                
                # Check image dimensions
                if width < 224 or height < 224:
                    validation_results['small_images'].append({
                        'filename': image.original_filename,
                        'size': f"{width}x{height}",
                        'class': image.class_name
                    })
                
                if width > 2048 or height > 2048:
                    validation_results['large_images'].append({
                        'filename': image.original_filename,
                        'size': f"{width}x{height}",
                        'class': image.class_name
                    })
                
                # Update class distribution
                class_name = image.class_name
                if class_name not in validation_results['class_distribution']:
                    validation_results['class_distribution'][class_name] = 0
                validation_results['class_distribution'][class_name] += 1
                
        except Exception as e:
            validation_results['corrupted_images'].append({
                'filename': image.original_filename,
                'reason': str(e)
            })
    
    # Generate recommendations
    if len(validation_results['corrupted_images']) > 0:
        validation_results['recommendations'].append(
            f"Remove {len(validation_results['corrupted_images'])} corrupted images"
        )
        validation_results['is_training_ready'] = False
    
    if len(validation_results['class_distribution']) < 2:
        validation_results['recommendations'].append(
            "Add more classes - at least 2 classes are required for training"
        )
        validation_results['is_training_ready'] = False
    
    # Check class balance
    class_counts = list(validation_results['class_distribution'].values())
    if class_counts:
        min_count = min(class_counts)
        max_count = max(class_counts)
        if min_count > 0 and (max_count / min_count) > 10:
            validation_results['recommendations'].append(
                "Dataset is imbalanced - consider adding more images to underrepresented classes"
            )
    
    if len(validation_results['small_images']) > validation_results['total_images'] * 0.1:
        validation_results['recommendations'].append(
            f"Many images ({len(validation_results['small_images'])}) are smaller than 224x224 pixels"
        )
    
    # Calculate percentages for class distribution
    class_distribution_with_percentages = {}
    if validation_results['total_images'] > 0:
        for class_name, count in validation_results['class_distribution'].items():
            percentage = (count * 100.0) / validation_results['total_images']
            class_distribution_with_percentages[class_name] = {
                'count': count,
                'percentage': round(percentage, 1)
            }
    
    validation_results['class_distribution_with_percentages'] = class_distribution_with_percentages
    
    context = {
        'dataset': dataset,
        'validation_results': validation_results,
    }
    
    return render(request, 'dataset_management/dataset_validation.html', context)


@login_required
@admin_required
def dataset_cleaning(request, pk):
    """
    Clean and edit dataset before training
    """
    dataset = get_object_or_404(Dataset, pk=pk)
    
    if dataset.status != 'completed':
        messages.error(request, 'Dataset must be completed before cleaning.')
        return redirect('dataset_management:dataset_detail', pk=pk)
    
    # Get class distribution
    classes = DatasetClass.objects.filter(dataset=dataset).order_by('class_name')
    
    # Get images with pagination
    images = DatasetImage.objects.filter(dataset=dataset).order_by('class_name', 'original_filename')
    
    # Filter by class if specified
    selected_class = request.GET.get('class')
    if selected_class:
        images = images.filter(class_name=selected_class)
    
    # Pagination
    paginator = Paginator(images, 24)  # 24 images per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'dataset': dataset,
        'classes': classes,
        'page_obj': page_obj,
        'selected_class': selected_class,
    }
    
    return render(request, 'dataset_management/dataset_cleaning.html', context)


@login_required
@admin_required
@csrf_exempt
def delete_image(request, pk):
    """
    Delete an image from the dataset
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    dataset = get_object_or_404(Dataset, pk=pk)
    image_id = request.POST.get('image_id')
    
    try:
        image = DatasetImage.objects.get(id=image_id, dataset=dataset)
        
        # Delete physical file
        if os.path.exists(image.image.path):
            os.remove(image.image.path)
        
        # Delete database record
        class_name = image.class_name
        image.delete()
        
        # Update class count
        try:
            dataset_class = DatasetClass.objects.get(dataset=dataset, class_name=class_name)
            dataset_class.image_count = DatasetImage.objects.filter(
                dataset=dataset, class_name=class_name
            ).count()
            dataset_class.save()
            
            # If no images left in class, delete the class
            if dataset_class.image_count == 0:
                dataset_class.delete()
        except DatasetClass.DoesNotExist:
            pass
        
        # Update dataset totals
        dataset.total_images = DatasetImage.objects.filter(dataset=dataset).count()
        dataset.total_classes = DatasetClass.objects.filter(dataset=dataset).count()
        dataset.save()
        
        return JsonResponse({'success': True})
        
    except DatasetImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@admin_required
@csrf_exempt
def rename_class(request, pk):
    """
    Rename a class in the dataset
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    dataset = get_object_or_404(Dataset, pk=pk)
    old_name = request.POST.get('old_name')
    new_name = request.POST.get('new_name')
    
    if not old_name or not new_name:
        return JsonResponse({'success': False, 'error': 'Both old and new names are required'})
    
    if old_name == new_name:
        return JsonResponse({'success': False, 'error': 'New name must be different'})
    
    # Check if new name already exists
    if DatasetClass.objects.filter(dataset=dataset, class_name=new_name).exists():
        return JsonResponse({'success': False, 'error': 'Class name already exists'})
    
    try:
        # Update class name in DatasetClass
        dataset_class = DatasetClass.objects.get(dataset=dataset, class_name=old_name)
        dataset_class.class_name = new_name
        dataset_class.save()
        
        # Update class name in all images
        DatasetImage.objects.filter(dataset=dataset, class_name=old_name).update(
            class_name=new_name
        )
        
        # Rename physical directory if it exists
        old_path = os.path.join(dataset.get_organized_path(), old_name)
        new_path = os.path.join(dataset.get_organized_path(), new_name)
        
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
        
        return JsonResponse({'success': True})
        
    except DatasetClass.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
