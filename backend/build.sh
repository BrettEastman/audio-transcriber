#!/bin/bash

# Audio Transcriber Backend Build Script
echo "🔨 Building Audio Transcriber Backend..."

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/

# Build with PyInstaller
echo "📦 Building with PyInstaller..."
pyinstaller main.spec

# Check if build was successful
if [ -f "dist/main_with_assets-aarch64-apple-darwin" ]; then
    echo "✅ Build successful! Executable created: dist/main_with_assets-aarch64-apple-darwin"
    echo "📊 File size: $(ls -lh dist/main_with_assets-aarch64-apple-darwin | awk '{print $5}')"

    # Create symlinks for Tauri compatibility
    echo "🔗 Creating symlinks for Tauri compatibility..."
    ln -sf main_with_assets-aarch64-apple-darwin dist/main_with_assets
    echo "✅ Symlinks created for Tauri build"
else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi

echo ""
echo "🎯 Next steps:"
echo "1. Build the Tauri app: cd ../frontend && npm run tauri build"
echo "2. Or test the backend directly: ./dist/main_with_assets-aarch64-apple-darwin"
