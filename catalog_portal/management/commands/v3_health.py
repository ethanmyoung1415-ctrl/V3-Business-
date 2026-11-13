import json
from django.core.management.base import BaseCommand,CommandError
from catalog_portal import health

class Command(BaseCommand):
    help="Read-only synthetic V3 operational status; no customer data printed"
    def add_arguments(self,parser):
        parser.add_argument("--fail-on-critical",action="store_true")
    def handle(self,*args,**options):
        report=health.snapshot()
        self.stdout.write(json.dumps(report,indent=2))
        if options["fail_on_critical"] and report["status"]=="critical":
            raise CommandError("Local V3 health check found critical operating conditions")
