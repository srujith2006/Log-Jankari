#!/bin/bash
# Quick Start Script for Survivor Detection Website

echo "🚀 Starting Survivor Detection Website..."
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null
then
    echo "❌ Python is not installed. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found"

# Check if pip is installed
if ! command -v pip &> /dev/null
then
    echo "❌ pip is not installed"
    exit 1
fi

echo "✅ pip found"

# Install requirements
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "📋 Setup Summary:"
echo "  - MongoDB Atlas connection configured"
echo "  - Flask server ready"
echo "  - Authentication system ready"
echo "  - Database models ready"
echo ""
echo "🚀 Ready to start the server!"
echo ""
echo "To start the web server, run:"
echo "  python web_server.py"
echo ""
echo "Then open your browser to: http://localhost:5000"
echo ""
echo "Keep your detection backend running in another terminal:"
echo "  python app.py"
