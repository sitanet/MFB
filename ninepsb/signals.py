import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from customers.models import Customer

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Customer)
def create_virtual_account_on_customer_creation(sender, instance, created, **kwargs):
    """
    Automatically create a virtual account when a new customer is created.
    Only triggers for new customers (created=True) and when they have the required information.
    """
    if not created:
        return  # Only process new customers
    
    # Check if customer already has a virtual account
    if instance.wallet_account:
        logger.info(f"Customer {instance.id} already has virtual account: {instance.wallet_account}")
        return
    
    # Ensure customer has minimum required information
    if not instance.get_full_name() or instance.get_full_name().strip() == "":
        logger.warning(f"Customer {instance.id} doesn't have a valid name, skipping virtual account creation")
        return
    
    try:
        # Import here to avoid circular imports
        from ninepsb.services import create_virtual_account_for_customer
        
        logger.info(f"Creating virtual account for new customer: {instance.id} - {instance.get_full_name()}")
        
        # Create virtual account
        va_details = create_virtual_account_for_customer(instance)
        
        if va_details and va_details.get("account_number"):
            logger.info(f"✅ Successfully created virtual account {va_details['account_number']} for customer {instance.id}")
        else:
            logger.error(f"❌ Virtual account creation returned no account number for customer {instance.id}")
            
    except Exception as e:
        logger.error(f"❌ Failed to create virtual account for customer {instance.id}: {str(e)}")
        # Don't raise the exception to avoid breaking customer creation
        # The virtual account can be created later manually or via retry mechanism