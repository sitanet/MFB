from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Branch


@receiver(post_save, sender=Branch)
def create_default_accounts(sender, instance, created, **kwargs):
    """Create default chart of accounts when a new branch is created"""
    if created:
        from accounts_admin.models import Account
        
        default_accounts = [
            {'gl_no': '10000', 'gl_name': 'ASSETS', 'account_type': Account.ASSETS},
            {'gl_no': '20000', 'gl_name': 'LIABILITIES', 'account_type': Account.LIABILITIES},
            {'gl_no': '30000', 'gl_name': 'EQUITY', 'account_type': Account.EQUITY},
            {'gl_no': '40000', 'gl_name': 'INCOMES', 'account_type': Account.INCOME},
            {'gl_no': '50000', 'gl_name': 'EXPENSES', 'account_type': Account.EXPENSES},
        ]
        
        for acc_data in default_accounts:
            Account.all_objects.create(
                branch=instance,
                gl_no=acc_data['gl_no'],
                gl_name=acc_data['gl_name'],
                account_type=acc_data['account_type'],
            )
