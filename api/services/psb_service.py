# api/services/psb_service.py
"""
BACKWARD COMPATIBILITY WRAPPER

This service has been replaced by enhanced_psb_service.py
This file now provides backward compatibility by redirecting to the enhanced service.
"""
import logging

logger = logging.getLogger(__name__)

# Import the enhanced service for backward compatibility
try:
    from .enhanced_psb_service import enhanced_psb_service as _enhanced_service
    
    class NinePSBVirtualAccountService:
        """Backward compatibility wrapper for the enhanced 9PSB service"""
        
        def __init__(self):
            logger.warning("NinePSBVirtualAccountService is deprecated. Use Enhanced9PSBService instead.")
            
        def create_virtual_account(self, customer_data=None, **kwargs):
            """Redirect to enhanced service with same parameters"""
            return _enhanced_service.create_virtual_account(customer_data, **kwargs)
            
        def authenticate(self):
            """Redirect to enhanced service authentication"""
            return _enhanced_service.authenticate()
    
    # Create instance for backward compatibility
    nine_psb_service = NinePSBVirtualAccountService()
    
    logger.info("✅ Using enhanced 9PSB service with backward compatibility wrapper")
    
except ImportError as e:
    logger.error(f"Enhanced PSB service not found: {e}")
    logger.error("Falling back to stub service. Some functionality may not work.")
    
    # Simple stub service that raises helpful errors
    class NinePSBVirtualAccountService:
        """Stub service when enhanced service is not available"""
        
        def __init__(self):
            self.error_msg = "Enhanced PSB service not available. Please ensure enhanced_psb_service.py is properly configured."
            
        def create_virtual_account(self, customer_data=None, **kwargs):
            """Stub method that raises informative error"""
            raise ImportError(self.error_msg)
            
        def authenticate(self):
            """Stub method that raises informative error"""
            raise ImportError(self.error_msg)
    
    # Create stub instance
    nine_psb_service = NinePSBVirtualAccountService()