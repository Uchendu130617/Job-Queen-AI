import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when critical configuration is missing or invalid"""
    pass


def validate_environment():
    """Validate all required environment variables for production"""
    
    required_vars = {
        'MONGO_URL': 'Database connection string',
        'DB_NAME': 'Database name',
        'JWT_SECRET': 'JWT secret key for token signing',
        'EMERGENT_LLM_KEY': 'AI service API key'
    }
    
    missing = []
    warnings = []
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing.append(f"{var} ({description})")
        elif var == 'JWT_SECRET':
            # Validate JWT secret strength
            if len(value) < 32:
                warnings.append(f"JWT_SECRET is too short (minimum 32 characters recommended)")
            if value == 'your-secret-key' or 'change' in value.lower():
                missing.append(f"JWT_SECRET must be changed from default value")
    
    # Check admin credentials
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_password and len(admin_password) < 8:
        warnings.append("ADMIN_PASSWORD should be at least 8 characters")
    
    if admin_password in ['admin123', 'password', '12345678']:
        warnings.append("ADMIN_PASSWORD is too weak - change immediately!")
    
    # Check CORS configuration
    cors_origins = os.environ.get('CORS_ORIGINS', '*')
    if cors_origins == '*':
        warnings.append("CORS_ORIGINS is set to '*' (allow all). Configure specific domains for production.")
    
    # Report findings
    if missing:
        error_msg = "Missing or invalid required configuration:\\n" + "\\n".join(f"  - {var}" for var in missing)
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    if warnings:
        warning_msg = "Configuration warnings:\\n" + "\\n".join(f"  - {warn}" for warn in warnings)
        logger.warning(warning_msg)
        print(f"\\n⚠️  {warning_msg}\\n")
    
    logger.info("✓ Environment configuration validated")
    return True


def get_config():
    """Get validated configuration object"""
    
    config = {
        # Database
        'MONGO_URL': os.environ.get('MONGO_URL'),
        'DB_NAME': os.environ.get('DB_NAME'),
        
        # Security
        'JWT_SECRET': os.environ.get('JWT_SECRET'),
        'ADMIN_EMAIL': os.environ.get('ADMIN_EMAIL', 'admin@jobquick.ai'),
        'ADMIN_PASSWORD': os.environ.get('ADMIN_PASSWORD', 'admin123'),
        
        # AI
        'EMERGENT_LLM_KEY': os.environ.get('EMERGENT_LLM_KEY'),
        'AI_PROVIDER': os.environ.get('AI_PROVIDER', 'openai'),
        'AI_MODEL': os.environ.get('AI_MODEL', 'gpt-5.2'),
        
        # CORS
        'CORS_ORIGINS': os.environ.get('CORS_ORIGINS', '*'),
        
        # File Upload
        'MAX_UPLOAD_SIZE_MB': int(os.environ.get('MAX_UPLOAD_SIZE_MB', 5)),
        'ALLOWED_EXTENSIONS': os.environ.get('ALLOWED_EXTENSIONS', '.pdf,.docx,.txt').split(','),
        
        # Feature Flags
        'ENABLE_SIGNUP': os.environ.get('ENABLE_SIGNUP', 'true').lower() == 'true',
        'AUTO_APPROVE_EMPLOYERS': os.environ.get('AUTO_APPROVE_EMPLOYERS', 'false').lower() == 'true',
        'AUTO_APPROVE_JOBS': os.environ.get('AUTO_APPROVE_JOBS', 'false').lower() == 'true',
        
        # Business Config
        'FREE_TIER_CREDITS': int(os.environ.get('FREE_TIER_CREDITS', 10)),
        'PROFESSIONAL_TIER_CREDITS': int(os.environ.get('PROFESSIONAL_TIER_CREDITS', 100)),
        'ENTERPRISE_TIER_CREDITS': int(os.environ.get('ENTERPRISE_TIER_CREDITS', 500)),
    }
    
    return config


def log_startup_info():
    """Log important startup information"""
    config = get_config()
    
    logger.info("=" * 60)
    logger.info("JobQuick AI - Starting Up")
    logger.info("=" * 60)
    logger.info(f"Database: {config['DB_NAME']}")
    logger.info(f"AI Provider: {config['AI_PROVIDER']} ({config['AI_MODEL']})")
    logger.info(f"CORS Origins: {config['CORS_ORIGINS']}")
    logger.info(f"Signup Enabled: {config['ENABLE_SIGNUP']}")
    logger.info(f"Auto-approve Employers: {config['AUTO_APPROVE_EMPLOYERS']}")
    logger.info(f"Auto-approve Jobs: {config['AUTO_APPROVE_JOBS']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Allow running this script to validate environment
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        validate_environment()
        config = get_config()
        log_startup_info()
        print("\\n✅ Configuration is valid!\\n")
    except ConfigurationError as e:
        print(f"\\n❌ Configuration Error:\\n{e}\\n")
        sys.exit(1)
