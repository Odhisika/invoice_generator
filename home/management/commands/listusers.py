from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'List all users in the system'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('username')
        
        if not users:
            self.stdout.write('No users found.')
            return
        
        self.stdout.write('Users in the system:')
        self.stdout.write('-' * 50)
        
        for user in users:
            status = []
            if user.is_superuser:
                status.append('Admin')
            if user.is_staff:
                status.append('Staff')
            if not user.is_active:
                status.append('Inactive')
            
            status_str = f" ({', '.join(status)})" if status else ""
            
            self.stdout.write(f'{user.username} - {user.email}{status_str}')
