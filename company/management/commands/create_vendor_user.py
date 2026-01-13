from django.core.management.base import BaseCommand
from company.models import VendorUser


class Command(BaseCommand):
    help = 'Create a vendor user for company/branch management'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Vendor email address')
        parser.add_argument('--username', type=str, required=True, help='Vendor username')
        parser.add_argument('--password', type=str, required=True, help='Vendor password')
        parser.add_argument('--first_name', type=str, required=True, help='First name')
        parser.add_argument('--last_name', type=str, required=True, help='Last name')
        parser.add_argument('--phone', type=str, default='', help='Phone number')
        parser.add_argument('--supervendor', action='store_true', help='Create as supervendor')

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        phone = options['phone']
        is_supervendor = options['supervendor']

        if VendorUser.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Vendor user with email "{email}" already exists.'))
            return

        if VendorUser.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'Vendor user with username "{username}" already exists.'))
            return

        if is_supervendor:
            user = VendorUser.objects.create_superuser(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
            )
            self.stdout.write(self.style.SUCCESS(f'Supervendor user "{email}" created successfully!'))
        else:
            user = VendorUser.objects.create_user(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
            )
            self.stdout.write(self.style.SUCCESS(f'Vendor user "{email}" created successfully!'))
