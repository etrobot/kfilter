#!/usr/bin/env python3
"""
Script to create PWA icons in various sizes from a source image
"""

import os
from PIL import Image
import json

def create_pwa_icons(source_image_path, output_dir="icons"):
    """Create PWA icons in various sizes"""
    
    # Standard PWA icon sizes
    sizes = [
        16, 32, 48, 72, 96, 128, 144, 152, 180, 192, 256, 384, 512, 1024
    ]
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Open source image
    try:
        with Image.open(source_image_path) as img:
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            created_icons = []
            
            # Create icons for each size
            for size in sizes:
                # Resize image
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                
                # Save as PNG
                output_path = os.path.join(output_dir, f"icon-{size}x{size}.png")
                resized.save(output_path, "PNG", optimize=True)
                created_icons.append({
                    "src": f"icons/icon-{size}x{size}.png",
                    "sizes": f"{size}x{size}",
                    "type": "image/png"
                })
                print(f"Created: {output_path}")
            
            # Create favicon.ico (16x16, 32x32, 48x48)
            favicon_sizes = [16, 32, 48]
            favicon_images = []
            for size in favicon_sizes:
                favicon_img = img.resize((size, size), Image.Resampling.LANCZOS)
                favicon_images.append(favicon_img)
            
            favicon_path = os.path.join(output_dir, "favicon.ico")
            favicon_images[0].save(
                favicon_path, 
                format='ICO', 
                sizes=[(s, s) for s in favicon_sizes],
                append_images=favicon_images[1:]
            )
            print(f"Created: {favicon_path}")
            
            # Create Apple touch icons
            apple_sizes = [57, 60, 72, 76, 114, 120, 144, 152, 180]
            for size in apple_sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                output_path = os.path.join(output_dir, f"apple-touch-icon-{size}x{size}.png")
                resized.save(output_path, "PNG", optimize=True)
                print(f"Created: {output_path}")
            
            # Create manifest.json
            manifest = {
                "name": "Stock Market Analysis",
                "short_name": "StockAnalysis",
                "description": "Professional stock market analysis application",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#ffffff",
                "theme_color": "#2563eb",
                "icons": created_icons
            }
            
            manifest_path = os.path.join(output_dir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            print(f"Created: {manifest_path}")
            
            # Create HTML meta tags file
            html_meta = f"""<!-- PWA Meta Tags -->
<link rel="manifest" href="icons/manifest.json">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="StockAnalysis">

<!-- Favicon -->
<link rel="icon" type="image/x-icon" href="icons/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="icons/icon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="icons/icon-32x32.png">

<!-- Apple Touch Icons -->
<link rel="apple-touch-icon" sizes="57x57" href="icons/apple-touch-icon-57x57.png">
<link rel="apple-touch-icon" sizes="60x60" href="icons/apple-touch-icon-60x60.png">
<link rel="apple-touch-icon" sizes="72x72" href="icons/apple-touch-icon-72x72.png">
<link rel="apple-touch-icon" sizes="76x76" href="icons/apple-touch-icon-76x76.png">
<link rel="apple-touch-icon" sizes="114x114" href="icons/apple-touch-icon-114x114.png">
<link rel="apple-touch-icon" sizes="120x120" href="icons/apple-touch-icon-120x120.png">
<link rel="apple-touch-icon" sizes="144x144" href="icons/apple-touch-icon-144x144.png">
<link rel="apple-touch-icon" sizes="152x152" href="icons/apple-touch-icon-152x152.png">
<link rel="apple-touch-icon" sizes="180x180" href="icons/apple-touch-icon-180x180.png">

<!-- Android Chrome Icons -->
<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192x192.png">
<link rel="icon" type="image/png" sizes="512x512" href="icons/icon-512x512.png">
"""
            
            html_meta_path = os.path.join(output_dir, "pwa-meta-tags.html")
            with open(html_meta_path, 'w') as f:
                f.write(html_meta)
            print(f"Created: {html_meta_path}")
            
            print(f"\n✅ Successfully created PWA icons in {len(sizes)} sizes!")
            print(f"📁 All files saved to: {output_dir}/")
            print(f"📱 Include the meta tags from pwa-meta-tags.html in your HTML head")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Use the generated icon
    source_image = "icons/generated_image_1.png"
    
    if os.path.exists(source_image):
        create_pwa_icons(source_image)
    else:
        print(f"❌ Source image not found: {source_image}")
        print("Please make sure the generated icon exists.")