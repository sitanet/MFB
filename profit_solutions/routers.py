class DatabaseRouter:
    """
    Routes database operations between vendor_db and default (client) database.
    """

    vendor_models = {
        'company.Company',
        'company.Branch',
    }

    def _model_label(self, app_label, model_name):
        # Django passes model_name in lowercase; normalize it properly
        return f"{app_label}.{model_name.capitalize()}"

    def db_for_read(self, model, **hints):
        model_label = f"{model._meta.app_label}.{model._meta.object_name}"
        return 'vendor_db' if model_label in self.vendor_models else 'default'

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db in {'default', 'vendor_db'} and obj2._state.db in {'default', 'vendor_db'}:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations go to the correct database.
        """
        if model_name:
            model_label = self._model_label(app_label, model_name)

            if db == 'vendor_db':
                # Allow ONLY Company and Branch
                return model_label in self.vendor_models

            if db == 'default':
                # Block Company and Branch from default DB
                return model_label not in self.vendor_models

        return None
