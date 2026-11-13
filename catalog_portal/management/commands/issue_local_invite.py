"""Issue a one-use *local synthetic* customer enrollment code."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from catalog_portal.models import Store
from catalog_portal import invitations

class Command(BaseCommand):
    help="Issue a synthetic local customer invitation, never email it"
    def add_arguments(self,parser):
        parser.add_argument("store_uuid")
        parser.add_argument("--operator",required=True)
        parser.add_argument("--hours",type=int,default=24)
    def handle(self,*args,**options):
        try:
            store=Store.objects.get(pk=options["store_uuid"])
            operator=get_user_model().objects.get(username=options["operator"])
            result=invitations.issue(store,operator,options["hours"])
        except (Store.DoesNotExist,get_user_model().DoesNotExist,
                ValueError,PermissionError) as ex:
            raise CommandError("Cannot issue invitation for the requested local store")
        self.stdout.write("SYNTHETIC SINGLE-USE INVITATION (shown once; not stored in plain text)")
        self.stdout.write("Code: "+result["code"])
        self.stdout.write("Expires at: "+result["expires_at"])
        self.stdout.write("Enter manually at http://127.0.0.1:8000/join-local-demo/")
        self.stdout.write("Do not share the code in GitHub, chat, email or public files.")
