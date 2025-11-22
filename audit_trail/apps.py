from django.apps import AppConfig


class AuditTrailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit_trail"
    verbose_name = "Audit Trail"
    
    def ready(self):
        import audit_trail.signals