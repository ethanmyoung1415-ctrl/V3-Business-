from django.core.management.base import BaseCommand
from catalog_portal.services import process_received_batch
class Command(BaseCommand):
    help="Process a limited batch of fictional/preproduction portal uploads"
    def add_arguments(self,parser):
        parser.add_argument("--limit",type=int,default=10)
    def handle(self,*args,**options):
        outcomes=process_received_batch(options["limit"])
        for outcome in outcomes:
            self.stdout.write(str(outcome))
        self.stdout.write(f"Processed/reviewed {len(outcomes)} submission(s)")
