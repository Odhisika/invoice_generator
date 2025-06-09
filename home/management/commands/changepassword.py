from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import getpass

class Command(BaseCommand):
    help = 'Change password for an existing user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to change password for')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist!')
            )
            return
        
        # Get new password securely
        while True:
            password = getpass.getpass('New password: ')
            password_confirm = getpass.getpass('Confirm new password: ')
            
            if password == password_confirm:
                break
            else:
                self.stdout.write(
                    self.style.ERROR('Passwords do not match. Try again.')
                )
        
        # Change password
        user.set_password(password)
        user.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully changed password for user "{username}"')
        )