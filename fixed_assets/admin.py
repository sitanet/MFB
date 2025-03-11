from django.contrib import admin
from .models import FixedAsset, AssetType, AssetGroup,  AssetClass, AssetLocation, Department,  Officer,  DepreciationMethod  


# Register your models here.
admin.site.register(FixedAsset)
admin.site.register(AssetType)
admin.site.register(AssetClass)
admin.site.register(AssetLocation)
admin.site.register(Department)
admin.site.register(Officer)
admin.site.register(DepreciationMethod)

admin.site.register(AssetGroup)
