# resize_icons.py
from PIL import Image
import os

def resize_icons():
    # Create assets folder if not exists
    if not os.path.exists('assets'):
        os.makedirs('assets')
    
    try:
        # Load your original icon (e.g., 192x192 or larger)
        original_icon = Image.open('icon 1.png')
        
        # Convert to 192x192 (square) by cropping if needed
        if original_icon.size != (192, 192):
            # Crop to square or resize
            width, height = original_icon.size
            min_dim = min(width, height)
            
            # Crop center square
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = (width + min_dim) // 2
            bottom = (height + min_dim) // 2
            
            squared_icon = original_icon.crop((left, top, right, bottom))
            squared_icon = squared_icon.resize((192, 192))
        else:
            squared_icon = original_icon
        
        # Required sizes for Android
        sizes = [36, 48, 72, 96, 144, 192]
        
        for size in sizes:
            # Use LANCZOS for high-quality resizing
            resized_icon = squared_icon.resize((size, size), Image.Resampling.LANCZOS)
            resized_icon.save(f'assets/icon-{size}.png')
            print(f"✅ Created icon-{size}.png")

        # Save the main 192x192 icon that buildozer uses by default
        squared_icon.save('assets/icon.png')
        print(f"✅ Created main assets/icon.png")

        print("✅ All icons created successfully!")
        
    except FileNotFoundError:
        print("❌ 'icon 1.png' not found. Please make sure the file is in the same directory.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    resize_icons()