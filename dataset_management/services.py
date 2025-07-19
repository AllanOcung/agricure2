import zipfile
import os
import tempfile
import shutil
from PIL import Image
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
import logging

from .models import Dataset, DatasetImage, DatasetClass

logger = logging.getLogger('dataset_management')


def process_dataset_upload(dataset_id):
    """
    Process uploaded dataset ZIP file
    Extract and organize by dataset folder structure for training libraries
    """
    
    try:
        dataset = Dataset.objects.get(id=dataset_id)
        dataset.status = 'processing'
        dataset.processing_log = 'Starting dataset processing...\n'
        dataset.save()
        
        # Create dataset-specific directory in media/datasets/
        dataset_folder_name = f"dataset_{dataset.id:03d}_{dataset.name.lower().replace(' ', '_')}_v1"
        dataset_media_path = os.path.join(settings.MEDIA_ROOT, 'datasets', dataset_folder_name)
        
        # Ensure the datasets directory exists
        os.makedirs(dataset_media_path, exist_ok=True)
        
        dataset.processing_log += f'Created dataset directory: {dataset_folder_name}\n'
        dataset.save()
        
        # Extract ZIP file to temporary directory first
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(dataset.zip_file.path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            dataset.processing_log += 'ZIP file extracted to temporary directory.\n'
            dataset.save()
            
            # Process and organize extracted contents
            image_count = 0
            class_count = 0
            processed_classes = {}
            
            # Walk through extracted directory
            for root, dirs, files in os.walk(temp_dir):
                # Skip root directory
                if root == temp_dir:
                    continue
                
                # Get class name from directory
                class_name = os.path.basename(root)
                
                # Skip hidden directories
                if class_name.startswith('.'):
                    continue
                
                # Create class directory in dataset folder
                class_dir = os.path.join(dataset_media_path, class_name)
                os.makedirs(class_dir, exist_ok=True)
                
                # Process images in this class
                class_images = []
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                        source_path = os.path.join(root, file)
                        
                        try:
                            # Process and copy image to organized structure
                            image_data = process_and_organize_image(
                                source_path, file, class_name, class_dir, dataset
                            )
                            if image_data:
                                class_images.append(image_data)
                                image_count += 1
                        
                        except Exception as e:
                            logger.warning(f'Failed to process image {file}: {str(e)}')
                            dataset.processing_log += f'Warning: Failed to process {file}: {str(e)}\n'
                            dataset.save()
                
                # Create dataset class if we have images
                if class_images:
                    dataset_class, created = DatasetClass.objects.get_or_create(
                        dataset=dataset,
                        class_name=class_name,
                        defaults={'image_count': len(class_images)}
                    )
                    
                    if not created:
                        dataset_class.image_count = len(class_images)
                        dataset_class.save()
                    
                    processed_classes[class_name] = len(class_images)
                    class_count += 1
                    
                    dataset.processing_log += f'Organized class "{class_name}": {len(class_images)} images\n'
                    dataset.save()
            
            # Update dataset statistics
            dataset.total_images = image_count
            dataset.total_classes = class_count
            dataset.status = 'completed'
            dataset.processed_at = timezone.now()
            dataset.processing_log += f'\nProcessing completed successfully!\n'
            dataset.processing_log += f'Dataset organized in: {dataset_folder_name}\n'
            dataset.processing_log += f'Total images: {image_count}\n'
            dataset.processing_log += f'Total classes: {class_count}\n'
            dataset.processing_log += f'Classes: {", ".join(processed_classes.keys())}\n'
            dataset.processing_log += f'Ready for training with Keras/PyTorch!\n'
            dataset.save()
            
            logger.info(f'Dataset {dataset_id} organized successfully in {dataset_folder_name}: {image_count} images, {class_count} classes')
    
    except Dataset.DoesNotExist:
        logger.error(f'Dataset {dataset_id} not found')
        
    except Exception as e:
        logger.error(f'Error processing dataset {dataset_id}: {str(e)}')
        
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            dataset.status = 'failed'
            dataset.error_message = str(e)
            dataset.processing_log += f'\nError: {str(e)}\n'
            dataset.save()
        except:
            pass


def process_and_organize_image(source_path, filename, class_name, class_dir, dataset):
    """
    Process individual image file and organize in dataset structure
    """
    
    try:
        # Open and validate image
        with Image.open(source_path) as img:
            # Get image info
            width, height = img.size
            format_type = img.format
            
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Resize if too large (max 2048x2048)
            max_size = 2048
            if width > max_size or height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Generate organized filename
            base_name, ext = os.path.splitext(filename)
            organized_filename = f"{base_name}.jpg"  # Standardize to JPG
            organized_path = os.path.join(class_dir, organized_filename)
            
            # Handle filename conflicts
            counter = 1
            while os.path.exists(organized_path):
                organized_filename = f"{base_name}_{counter}.jpg"
                organized_path = os.path.join(class_dir, organized_filename)
                counter += 1
            
            # Save organized image
            img.save(organized_path, 'JPEG', quality=90)
            
            # Get file size
            file_size = os.path.getsize(organized_path)
            
            # Calculate relative path for database storage
            relative_path = os.path.relpath(organized_path, settings.MEDIA_ROOT)
            
            # Create DatasetImage record
            dataset_image = DatasetImage.objects.create(
                dataset=dataset,
                original_filename=filename,
                class_name=class_name,
                file_size=file_size,
                image_width=width,
                image_height=height
            )
            
            # Set the image field to point to the organized file
            dataset_image.image.name = relative_path
            dataset_image.save()
            
            return {
                'filename': organized_filename,
                'class_name': class_name,
                'width': width,
                'height': height,
                'file_size': file_size,
                'organized_path': organized_path
            }
    
    except Exception as e:
        logger.error(f'Error processing image {filename}: {str(e)}')
        return None


def validate_dataset_structure(zip_file_path):
    """
    Validate dataset ZIP file structure
    Expected structure:
    dataset.zip/
    ├── class1/
    │   ├── image1.jpg
    │   └── image2.jpg
    └── class2/
        ├── image3.jpg
        └── image4.jpg
    """
    
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            
            # Check for valid structure
            has_classes = False
            has_images = False
            
            for file_path in file_list:
                # Skip hidden files and directories
                if '.' in os.path.basename(file_path) and os.path.basename(file_path).startswith('.'):
                    continue
                
                path_parts = file_path.split('/')
                
                # Check if it's a class directory
                if len(path_parts) >= 2 and not file_path.endswith('/'):
                    has_classes = True
                    
                    # Check if it's an image file
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                        has_images = True
            
            return {
                'valid': has_classes and has_images,
                'has_classes': has_classes,
                'has_images': has_images,
                'total_files': len(file_list)
            }
    
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }


def get_dataset_preview(zip_file_path, max_classes=5, max_images_per_class=3):
    """
    Get a preview of dataset contents without full processing
    """
    
    try:
        preview = {
            'classes': {},
            'total_files': 0,
            'total_images': 0,
            'image_extensions': set()
        }
        
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            preview['total_files'] = len(file_list)
            
            for file_path in file_list:
                if file_path.endswith('/'):
                    continue
                
                path_parts = file_path.split('/')
                if len(path_parts) >= 2:
                    class_name = path_parts[-2]  # Parent directory name
                    filename = path_parts[-1]
                    
                    # Check if it's an image
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                        preview['total_images'] += 1
                        preview['image_extensions'].add(ext)
                        
                        if class_name not in preview['classes']:
                            preview['classes'][class_name] = []
                        
                        if len(preview['classes'][class_name]) < max_images_per_class:
                            preview['classes'][class_name].append(filename)
                
                # Limit number of classes shown
                if len(preview['classes']) >= max_classes:
                    break
        
        preview['image_extensions'] = list(preview['image_extensions'])
        return preview
    
    except Exception as e:
        return {'error': str(e)}
