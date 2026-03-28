#!/usr/bin/env python3
"""
Configuration validation script for Document Intelligence System.
This script validates that configuration loading works correctly
and displays the current settings.
"""

import os
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from app.config import get_settings, ensure_directories
except ImportError as e:
    print(f"❌ Failed to import config module: {e}")
    print(f"   Current Python path: {sys.path}")
    print(f"   Looking for backend directory at: {backend_dir}")
    sys.exit(1)


def validate_config():
    """Validate configuration loading and display settings."""
    print("=" * 60)
    print("Document Intelligence System - Configuration Validation")
    print("=" * 60)

    # Check environment files
    env_files = [
        Path(".env"),
        Path("../.env"),
        Path("../../.env"),
        Path("/app/.env"),
    ]

    print("\n🔍 Checking environment files:")
    found_env = False
    for env_path in env_files:
        if env_path.exists():
            print(f"   ✅ Found: {env_path.absolute()}")
            found_env = True
        else:
            print(f"   ❌ Not found: {env_path}")

    if not found_env:
        print("   ⚠️  No .env file found. Using default values.")

    # Load settings
    print("\n📋 Loading settings...")
    try:
        settings = get_settings()
        print("   ✅ Settings loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load settings: {e}")
        sys.exit(1)

    # Display settings (mask sensitive data)
    print("\n⚙️  Current Configuration:")
    print("   " + "-" * 40)

    # Application settings
    print(f"   Application:")
    print(f"     APP_NAME: {settings.APP_NAME}")
    print(f"     APP_VERSION: {settings.APP_VERSION}")
    print(f"     DEBUG: {settings.DEBUG}")
    print(f"     APP_ENV: {getattr(settings, 'APP_ENV', 'Not set')}")

    # Server settings
    print(f"\n   Server:")
    print(f"     HOST: {settings.HOST}")
    print(f"     PORT: {settings.PORT}")

    # Database settings
    print(f"\n   Database:")
    print(f"     DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    print(f"     DATABASE_POOL_SIZE: {settings.DATABASE_POOL_SIZE}")
    print(f"     DATABASE_MAX_OVERFLOW: {settings.DATABASE_MAX_OVERFLOW}")

    # Redis settings
    print(f"\n   Redis:")
    print(f"     REDIS_URL: {settings.REDIS_URL}")
    print(f"     REDIS_PASSWORD: {'[SET]' if settings.REDIS_PASSWORD else '[NOT SET]'}")

    # DeepSeek API settings
    print(f"\n   DeepSeek API:")
    api_key = settings.DEEPSEEK_API_KEY
    if api_key:
        if api_key.startswith("sk-test-"):
            print(f"     API_KEY: {api_key[:10]}... (test key)")
        else:
            print(f"     API_KEY: {api_key[:10]}... (production key)")
    else:
        print(f"     API_KEY: [NOT SET]")
    print(f"     API_BASE: {settings.DEEPSEEK_API_BASE}")
    print(f"     MODEL: {settings.DEEPSEEK_MODEL}")
    print(f"     MAX_TOKENS: {settings.DEEPSEEK_MAX_TOKENS}")
    print(f"     TEMPERATURE: {settings.DEEPSEEK_TEMPERATURE}")
    print(f"     TIMEOUT: {settings.DEEPSEEK_TIMEOUT}")

    # File upload settings
    print(f"\n   File Upload:")
    print(f"     MAX_UPLOAD_SIZE: {settings.MAX_UPLOAD_SIZE} bytes ({settings.MAX_UPLOAD_SIZE // (1024*1024)} MB)")
    print(f"     ALLOWED_EXTENSIONS: {settings.ALLOWED_EXTENSIONS}")

    # Path settings
    print(f"\n   Paths:")
    print(f"     BASE_DIR: {settings.BASE_DIR}")
    print(f"     UPLOAD_DIR: {settings.UPLOAD_DIR}")
    print(f"     TEMPLATE_DIR: {settings.TEMPLATE_DIR}")
    print(f"     OUTPUT_DIR: {settings.OUTPUT_DIR}")
    print(f"     LOG_DIR: {settings.LOG_DIR}")

    # Task processing
    print(f"\n   Task Processing:")
    print(f"     MAX_CONCURRENT_TASKS: {settings.MAX_CONCURRENT_TASKS}")
    print(f"     TASK_TIMEOUT: {settings.TASK_TIMEOUT} seconds")

    # Check directories
    print("\n📁 Checking directories:")
    try:
        ensure_directories()
        for dir_name, dir_path in [
            ("UPLOAD_DIR", settings.UPLOAD_DIR),
            ("TEMPLATE_DIR", settings.TEMPLATE_DIR),
            ("OUTPUT_DIR", settings.OUTPUT_DIR),
            ("LOG_DIR", settings.LOG_DIR),
        ]:
            if dir_path.exists():
                print(f"   ✅ {dir_name}: {dir_path} (exists)")
            else:
                print(f"   ⚠️  {dir_name}: {dir_path} (created)")
    except Exception as e:
        print(f"   ❌ Failed to create directories: {e}")

    # Check environment variables
    print("\n🌍 Environment variables (relevant):")
    env_vars_to_check = [
        "DEEPSEEK_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "DEBUG",
        "APP_ENV",
        "TEST_DATABASE_URL",
        "TEST_DEEPSEEK_API_KEY",
    ]

    for var in env_vars_to_check:
        value = os.getenv(var)
        if value:
            if "KEY" in var or "PASSWORD" in var:
                print(f"   ✅ {var}: {value[:10]}...")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: [NOT SET]")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY:")

    issues = []

    # Check for empty API key (warning, not error)
    if not settings.DEEPSEEK_API_KEY:
        issues.append("⚠️  DEEPSEEK_API_KEY is empty - LLM features will not work")

    # Check database URL (warning if using default localhost)
    if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
        issues.append("ℹ️  DATABASE_URL points to localhost - ensure MySQL is running")

    # Check Redis URL
    if "localhost" in settings.REDIS_URL:
        issues.append("ℹ️  REDIS_URL points to localhost - ensure Redis is running")

    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ No critical issues found")

    # Docker vs local check
    print("\n🏗️  Environment check:")
    if "mysql" in settings.DATABASE_URL and "redis" in settings.REDIS_URL:
        print("  ✅ Configuration appears to be for Docker deployment")
    else:
        print("  ℹ️  Configuration appears to be for local development")

    print("\n🎉 Validation complete!")
    print("=" * 60)


if __name__ == "__main__":
    validate_config()