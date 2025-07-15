import os

dataset_path = 'training_data'
total_images = 0

print('=== TOMATO DISEASE DATASET ANALYSIS ===')
print('Dataset structure:')
print()

classes = []
for class_dir in os.listdir(dataset_path):
    class_path = os.path.join(dataset_path, class_dir)
    if os.path.isdir(class_path):
        image_files = [f for f in os.listdir(class_path) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_count = len(image_files)
        total_images += image_count
        classes.append((class_dir, image_count))
        print(f'{class_dir}: {image_count} images')

print(f'\nTotal images: {total_images}')
print(f'Number of classes: {len(classes)}')
print()

# Check for balanced dataset
print('Dataset balance:')
avg_images = total_images / len(classes) if classes else 0
for class_name, count in classes:
    percentage = (count / total_images) * 100 if total_images > 0 else 0
    balance_status = "✓ Balanced" if abs(count - avg_images) < avg_images * 0.2 else "⚠ Imbalanced"
    print(f'{class_name}: {percentage:.1f}% - {balance_status}')

print(f'\nDataset is ready for training!')
print(f'Recommended training parameters:')
print(f'- Batch size: 16-32 (depending on GPU memory)')
print(f'- Epochs: 20-30')
print(f'- Learning rate: 0.001 (with transfer learning)')
