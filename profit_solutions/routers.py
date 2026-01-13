class DatabaseRouter:
    """
    Routes database operations to default database.
    
    Note: vendor_db routing is disabled. All models use the default database.
    To enable multi-database setup, uncomment vendor_db in settings.py DATABASES
    and restore the original routing logic.
    """

    vendor_models = {
        'company.Company',
        'company.Branch',
    }

    def _model_label(self, app_label, model_name):
        # Django passes model_name in lowercase; normalize it properly
        return f"{app_label}.{model_name.capitalize()}"

    def db_for_read(self, model, **hints):
        # All models use default database
        return 'default'

    def db_for_write(self, model, **hints):
        # All models use default database
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow all relations within default database
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All migrations go to default database.
        """
        return db == 'default'
