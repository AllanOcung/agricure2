"""
Dataset Cleaning Script - Find and Remove Corrupted Images
"""

import os
import shutil
from PIL import Image
import cv2
import numpy as np
from pathlib import Path

def validate_image_file(image_path):
    """
    Validate if an image file can be properly loaded
    
    Args:
        image_path: Path to image file
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Test with PIL
        with Image.open(image_path) as img:
            img.verify()  # Verify image integrity
            
        # Re-open and test conversion (verify() closes the file)
        with Image.open(image_path) as img:
            img.convert('RGB')  # Test color conversion
            
        # Test with OpenCV as secondary validation
        cv_img = cv2.imread(str(image_path))
        if cv_img is None:
            return False, "OpenCV cannot read image"
            
        # Check if image has valid dimensions
        if cv_img.shape[0] < 10 or cv_img.shape[1] < 10:
            return False, "Image too small (< 10x10 pixels)"
            
        return True, "Valid"
        
    except Exception as e:
        return False, str(e)

def get_file_info(file_path):
    """Get basic file information"""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'exists': True
        }
    except:
        return {
            'size': 0,
            'exists': False
        }

def clean_dataset(dataset_path, backup_corrupted=True):
    """
    Clean dataset by removing corrupted images
    
    Args:
        dataset_path: Path to dataset directory
        backup_corrupted: Whether to backup corrupted files instead of deleting
    """
    dataset_path = Path(dataset_path)
    
    if not dataset_path.exists():
        print(f"Dataset path does not exist: {dataset_path}")
        return
    
    # Create backup directory for corrupted files if needed
    if backup_corrupted:
        backup_dir = dataset_path.parent / f"{dataset_path.name}_corrupted_backup"
        backup_dir.mkdir(exist_ok=True)
        print(f"Corrupted files will be backed up to: {backup_dir}")
    
    # Image extensions to check
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    total_files = 0
    corrupted_files = 0
    valid_files = 0
    small_files = 0
    
    print("Scanning dataset for corrupted images...")
    print("=" * 60)
    
    # Walk through all subdirectories
    for class_dir in dataset_path.iterdir():
        if not class_dir.is_dir():
            continue
            
        class_name = class_dir.name
        print(f"\nProcessing class: {class_name}")
        print("-" * 40)
        
        class_total = 0
        class_corrupted = 0
        class_valid = 0
        
        # Create backup subdirectory for this class if needed
        if backup_corrupted:
            class_backup_dir = backup_dir / class_name
            class_backup_dir.mkdir(exist_ok=True)
        
        for image_file in class_dir.iterdir():
            if not image_file.is_file():
                continue
                
            # Check if it's an image file
            if image_file.suffix.lower() not in image_extensions:
                continue
                
            class_total += 1
            total_files += 1
            
            # Get file info
            file_info = get_file_info(image_file)
            
            # Check for very small files (likely corrupted)
            if file_info['size'] < 1024:  # Less than 1KB
                print(f"  ⚠️  Very small file: {image_file.name} ({file_info['size']} bytes)")
                small_files += 1
            
            # Validate image
            is_valid, error_msg = validate_image_file(image_file)
            
            if not is_valid:
                print(f"  ❌ CORRUPTED: {image_file.name} - {error_msg}")
                class_corrupted += 1
                corrupted_files += 1
                
                # Handle corrupted file
                if backup_corrupted:
                    # Move to backup directory
                    backup_path = class_backup_dir / image_file.name
                    shutil.move(str(image_file), str(backup_path))
                    print(f"     → Moved to backup: {backup_path}")
                else:
                    # Delete the file
                    image_file.unlink()
                    print(f"     → Deleted")
            else:
                class_valid += 1
                valid_files += 1
                
        print(f"  Class summary: {class_valid} valid, {class_corrupted} corrupted out of {class_total} total")
    
    print("\n" + "=" * 60)
    print("DATASET CLEANING SUMMARY")
    print("=" * 60)
    print(f"Total files processed: {total_files}")
    print(f"Valid images: {valid_files}")
    print(f"Corrupted images: {corrupted_files}")
    print(f"Small files (< 1KB): {small_files}")
    print(f"Corruption rate: {(corrupted_files/total_files*100):.2f}%" if total_files > 0 else "No files found")
    
    if corrupted_files > 0:
        if backup_corrupted:
            print(f"\n✅ Corrupted files backed up to: {backup_dir}")
        else:
            print(f"\n✅ Corrupted files deleted")
        print("Dataset is now clean and ready for training!")
    else:
        print("\n✅ No corrupted files found. Dataset is clean!")
    
    return {
        'total_files': total_files,
        'valid_files': valid_files,
        'corrupted_files': corrupted_files,
        'small_files': small_files
    }

def analyze_class_distribution(dataset_path):
    """Analyze the distribution of images per class after cleaning"""
    dataset_path = Path(dataset_path)
    
    print("\n" + "=" * 60)
    print("CLASS DISTRIBUTION AFTER CLEANING")
    print("=" * 60)
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    for class_dir in sorted(dataset_path.iterdir()):
        if not class_dir.is_dir():
            continue
            
        # Count valid image files
        image_count = sum(1 for f in class_dir.iterdir() 
                         if f.is_file() and f.suffix.lower() in image_extensions)
        
        print(f"{class_dir.name}: {image_count} images")

if __name__ == "__main__":
    # Set your dataset path
    DATASET_PATH = "training_data"
    
    print("🧹 DATASET CLEANING TOOL")
    print("=" * 60)
    
    # Clean the dataset
    results = clean_dataset(DATASET_PATH, backup_corrupted=True)
    
    # Show class distribution after cleaning
    analyze_class_distribution(DATASET_PATH)
    
    print(f"\n🎯 Ready to restart training with clean dataset!")
