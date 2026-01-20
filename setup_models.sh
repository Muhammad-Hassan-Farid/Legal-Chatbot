#!/bin/bash

# HuggingFace Model Downloader Script
# This script downloads models to a local cache directory

PROJECT_DIR="/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot"
HF_CACHE_DIR="$PROJECT_DIR/hf_models"

echo "🔧 Setting up HuggingFace model cache..."
echo "📂 Cache directory: $HF_CACHE_DIR"

# Create directories
mkdir -p "$HF_CACHE_DIR/hub"

# Set environment variables
export HF_HOME="$HF_CACHE_DIR"
export HUGGINGFACE_HUB_CACHE="$HF_CACHE_DIR/hub"

echo "✅ Environment configured"
echo ""
echo "Run this to download models:"
echo "  cd $PROJECT_DIR"
echo "  export HF_HOME=$HF_CACHE_DIR"
echo "  python download_models.py"
echo ""
echo "Or for automatic setup in future sessions, add to your .bashrc or .zshrc:"
echo "  export HF_HOME=$HF_CACHE_DIR"
