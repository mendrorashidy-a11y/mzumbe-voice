from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist, using environment variables'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if not username:
            self.stdout.write(self.style.WARNING('DJANGO_SUPERUSER_USERNAME not set. Skipping.'))
            return
        if not email:
            self.stdout.write(self.style.WARNING('DJANGO_SUPERUSER_EMAIL not set. Skipping.'))
            return
        if not password:
            self.stdout.write(self.style.WARNING('DJANGO_SUPERUSER_PASSWORD not set. Skipping.'))
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} already exists.'))