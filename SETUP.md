# Menon Foundry OS - Setup Guide

## Prerequisites
- Python 3.9+
- Conda (recommended) or pip
- PostgreSQL (for database operations)

## Step 1: Install Dependencies

### Option A: Guided Installation (Recommended)
```bash
python setup_env.py
```

### Option B: Standard Installation
```bash
pip install -r requirements.txt
```

### Option C: Conda Installation
```bash
conda create -n foundry_os python=3.11
conda activate foundry_os
pip install -r requirements.txt
```

## Step 2: Configure Environment

1. Copy `.env.example` to `.env` (if available)
2. Update `.env` with your credentials:
   ```
   GROQ_API_KEY=your_groq_api_key
   NEWS_API_KEY=your_newsapi_key
   METAL_PRICE=your_metal_price_api_key
   DB_NAME=foundry_db
   DB_USER=postgres
   DB_PASS=your_password
   DB_HOST=localhost
   ```

## Step 3: Initialize Knowledge Base

```bash
python ingest_knowledge.py
```

You should see:
