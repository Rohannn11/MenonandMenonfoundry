"""
Setup script to install all dependencies in the correct order.
Run this if you have issues with pip install -r requirements.txt
"""

import subprocess
import sys

PACKAGES = [
    "pip>=24.0",
    "wheel",
    "setuptools",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
    "yfinance>=0.2.28",
    "sentence-transformers>=2.2.0",
    "chromadb>=0.4.0",
    "langchain-core>=0.1.0",
    "langchain>=0.1.0",
    "langchain-groq>=0.1.0",
    "groq>=0.4.0",
    "openai>=1.0.0",
    "psycopg2-binary>=2.9.0",
    "streamlit>=1.28.0",
]

def install_packages():
    """Install packages in correct order."""
    print("🚀 Installing packages in correct order...\n")
    
    failed = []
    for i, package in enumerate(PACKAGES, 1):
        print(f"[{i}/{len(PACKAGES)}] Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
            print(f"✅ {package} installed\n")
        except Exception as e:
            print(f"❌ Failed to install {package}: {e}\n")
            failed.append(package)
    
    if failed:
        print(f"\n⚠️  Failed packages: {', '.join(failed)}")
        print("Try installing manually: pip install <package>")
        return False
    else:
        print("\n✅ All packages installed successfully!")
        return True

if __name__ == "__main__":
    success = install_packages()
    sys.exit(0 if success else 1)
