"""
Management command to migrate existing Account records to use the company field.
This populates the company field based on the existing branch.company relationship.
"""
from django.core.management.base import BaseCommand
from accounts_admin.models import Account
from company.models import Company


class Command(BaseCommand):
    help = 'Migrate existing Account records to populate the company field based on branch.company'

    def handle(self, *args, **options):
        # Get all accounts that have a branch but no company set
        accounts_to_update = Account.all_objects.filter(
            branch__isnull=False,
            company__isnull=True
        ).select_related('branch__company')
        
        total = accounts_to_update.count()
        self.stdout.write(f"Found {total} accounts to update...")
        
        updated = 0
        errors = 0
        
        for account in accounts_to_update:
            try:
                if account.branch and account.branch.company:
                    account.company = account.branch.company
                    account.save(update_fields=['company'])
                    updated += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Account {account.gl_no} has no valid branch.company")
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error updating account {account.gl_no}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Migration complete: {updated} accounts updated, {errors} errors")
        )
        
        # Also remove duplicate accounts per company (keep one per gl_no per company)
        self.stdout.write("\nChecking for duplicate GL numbers per company...")
        
        companies = Company.objects.all()
        duplicates_removed = 0
        
        for company in companies:
            # Get all GL numbers for this company
            gl_numbers = Account.all_objects.filter(company=company).values_list('gl_no', flat=True)
            seen = set()
            
            for gl_no in gl_numbers:
                if gl_no in seen:
                    # This is a duplicate - get all accounts with this gl_no for this company
                    duplicates = Account.all_objects.filter(company=company, gl_no=gl_no).order_by('id')
                    # Keep the first one, delete the rest
                    for dup in duplicates[1:]:
                        self.stdout.write(f"Removing duplicate: Company={company.company_name}, GL={gl_no}")
                        dup.delete()
                        duplicates_removed += 1
                else:
                    seen.add(gl_no)
        
        self.stdout.write(
            self.style.SUCCESS(f"Removed {duplicates_removed} duplicate accounts")
        )
