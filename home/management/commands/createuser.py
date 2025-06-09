from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import getpass

class Command(BaseCommand):
    help = 'Create a new user for the receipt generator'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')
        parser.add_argument('email', type=str, help='Email for the new user')
        parser.add_argument('--admin', action='store_true', help='Make user an admin')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'User "{username}" already exists!')
            )
            return
        
        # Get password securely
        while True:
            password = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Confirm password: ')
            
            if password == password_confirm:
                break
            else:
                self.stdout.write(
                    self.style.ERROR('Passwords do not match. Try again.')
                )
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            if options['admin']:
                user.is_staff = True
                user.is_superuser = True
                user.save()
                
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {"admin " if options["admin"] else ""}user "{username}"'
                )
            )
            
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {e}')
            )