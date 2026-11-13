"""Bootstrap fictional trial accounts in LOCAL_DEV only. Never for customer use."""
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from catalog_portal.models import Store,Membership

class Command(BaseCommand):
    help="Create synthetic demo accounts (prints randomly generated one-time passwords)"
    def add_arguments(self,parser):
        parser.add_argument("--synthetic-only",action="store_true")
    def handle(self,*args,**options):
        if not getattr(settings,"LOCAL_DEV",False) or not options["synthetic_only"]:
            raise CommandError("demo seeding is disabled outside explicitly acknowledged local development")
        users=["v3-demo-operator","v3-demo-a","v3-demo-b"]
        User=get_user_model()
        if User.objects.filter(username__in=users).exists():
            raise CommandError("demo users already exist; refusing to replace credentials")
        credentials={name:secrets.token_urlsafe(22) for name in users}
        with transaction.atomic():
            operator=User.objects.create_user(username=users[0],password=credentials[users[0]])
            a=User.objects.create_user(username=users[1],password=credentials[users[1]])
            b=User.objects.create_user(username=users[2],password=credentials[users[2]])
            store_a=Store.objects.create(name="Demo Supplier Shop A")
            store_b=Store.objects.create(name="Demo Supplier Shop B")
            Membership.objects.bulk_create([
                Membership(user=operator,store=store_a,role="operator"),
                Membership(user=operator,store=store_b,role="operator"),
                Membership(user=a,store=store_a,role="customer"),
                Membership(user=b,store=store_b,role="customer"),
            ])
        self.stdout.write("SYNTHETIC LOCAL LOGIN CREDENTIALS (shown once; not stored in plaintext):")
        for username,password in credentials.items():
            self.stdout.write(f"{username}: {password}")
        self.stdout.write("Do not deploy this environment or use real customer files.")
