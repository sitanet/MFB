"""
Tenant-Aware Model Managers

These managers automatically filter querysets by the current tenant (branch).
This ensures data isolation between different cooperatives/thrift collectors.
"""

from django.db import models
from django.db.models import QuerySet


class TenantQuerySet(QuerySet):
    """
    Custom QuerySet that automatically filters by tenant.
    """
    
    def filter_by_tenant(self):
        """Apply tenant filter based on current context"""
        from profit_solutions.tenant_middleware import get_current_tenant
        
        branch_id = get_current_tenant()
        if branch_id:
            # Check which field to use for filtering
            if hasattr(self.model, 'branch_id'):
                return self.filter(branch_id=branch_id)
            elif hasattr(self.model, 'branch'):
                return self.filter(branch_id=branch_id)
        return self
    
    def for_tenant(self, branch_id):
        """Explicitly filter by a specific tenant"""
        if hasattr(self.model, 'branch_id'):
            return self.filter(branch_id=branch_id)
        elif hasattr(self.model, 'branch'):
            return self.filter(branch_id=branch_id)
        return self


class TenantManager(models.Manager):
    """
    Manager that automatically filters by the current tenant.
    
    Usage in models:
        class Customer(models.Model):
            branch = models.ForeignKey(Branch, ...)
            # ... other fields ...
            
            objects = TenantManager()  # Replaces default manager
            all_objects = models.Manager()  # Keep unfiltered access if needed
    """
    
    def get_queryset(self):
        """Override to automatically filter by tenant"""
        from profit_solutions.tenant_middleware import get_current_tenant
        
        qs = TenantQuerySet(self.model, using=self._db)
        branch_id = get_current_tenant()
        
        if branch_id:
            # Determine the correct field name for branch filtering
            if hasattr(self.model, 'branch'):
                return qs.filter(branch_id=branch_id)
            elif hasattr(self.model, 'branch_id'):
                return qs.filter(branch_id=branch_id)
        
        return qs
    
    def unfiltered(self):
        """Get unfiltered queryset (bypass tenant filtering)"""
        return TenantQuerySet(self.model, using=self._db)
    
    def for_tenant(self, branch_id):
        """Get queryset filtered by specific tenant"""
        return TenantQuerySet(self.model, using=self._db).filter(branch_id=branch_id)


class TenantManagerWithCustBranch(models.Manager):
    """
    Manager for models that use 'cust_branch' instead of 'branch' for tenant filtering.
    Used for models like Memtrans that have both branch and cust_branch fields.
    """
    
    def get_queryset(self):
        """Override to automatically filter by tenant using cust_branch"""
        from profit_solutions.tenant_middleware import get_current_tenant
        
        qs = TenantQuerySet(self.model, using=self._db)
        branch_id = get_current_tenant()
        
        if branch_id:
            return qs.filter(cust_branch_id=branch_id)
        
        return qs
    
    def unfiltered(self):
        """Get unfiltered queryset (bypass tenant filtering)"""
        return TenantQuerySet(self.model, using=self._db)


class CompanyTenantManager(models.Manager):
    """
    Manager that filters by company instead of branch.
    Useful when you want to show data across all branches of a company.
    """
    
    def get_queryset(self):
        """Override to automatically filter by company"""
        from profit_solutions.tenant_middleware import get_current_company, get_current_tenant
        
        qs = TenantQuerySet(self.model, using=self._db)
        company_id = get_current_company()
        
        if company_id:
            # Get all branch IDs for this company
            try:
                from company.models import Branch
                branch_ids = list(
                    Branch.objects
                    .filter(company_id=company_id)
                    .values_list('id', flat=True)
                )
                branch_ids = [str(bid) for bid in branch_ids]
                
                if hasattr(self.model, 'branch'):
                    return qs.filter(branch_id__in=branch_ids)
                elif hasattr(self.model, 'branch_id'):
                    return qs.filter(branch_id__in=branch_ids)
            except Exception:
                pass
        
        # Fallback to branch filtering
        branch_id = get_current_tenant()
        if branch_id:
            if hasattr(self.model, 'branch'):
                return qs.filter(branch_id=branch_id)
        
        return qs
    
    def unfiltered(self):
        """Get unfiltered queryset (bypass tenant filtering)"""
        return TenantQuerySet(self.model, using=self._db)
