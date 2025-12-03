"""
Database Helper Functions for Multi-Database Architecture

These functions help with cross-database queries between
the vendor database (Company/Branch) and client database (everything else).
"""

from django.core.exceptions import ObjectDoesNotExist


def get_branch_by_id(branch_id):
    """Get a branch from the vendor database by ID"""
    if not branch_id:
        return None
    
    try:
        from company.models import Branch
        return Branch.objects.using('vendor_db').get(id=branch_id)
    except ObjectDoesNotExist:
        return None


def get_company_by_id(company_id):
    """Get a company from the vendor database by ID"""
    if not company_id:
        return None
    
    try:
        from company.models import Company
        return Company.objects.using('vendor_db').get(id=company_id)
    except ObjectDoesNotExist:
        return None


def get_all_branches():
    """Get all branches from vendor database"""
    from company.models import Branch
    return Branch.objects.using('vendor_db').all()


def get_branches_for_company(company_id):
    """Get all branches for a specific company"""
    from company.models import Branch
    return Branch.objects.using('vendor_db').filter(company_id=company_id)


def create_branch_in_vendor_db(branch_data):
    """Create a new branch in the vendor database"""
    from company.models import Branch
    branch = Branch(**branch_data)
    branch.save(using='vendor_db')
    return branch


def update_branch_in_vendor_db(branch_id, update_data):
    """Update a branch in the vendor database"""
    try:
        from company.models import Branch
        branch = Branch.objects.using('vendor_db').get(id=branch_id)
        for field, value in update_data.items():
            setattr(branch, field, value)
        branch.save(using='vendor_db')
        return branch
    except ObjectDoesNotExist:
        return None


def get_users_for_branch(branch_id):
    """Get all users for a specific branch from client database"""
    from accounts.models import User
    return User.objects.filter(branch_id=str(branch_id))


def get_customers_for_branch(branch_id):
    """Get all customers for a specific branch from client database"""
    from customers.models import Customer
    return Customer.objects.filter(branch_id=str(branch_id))