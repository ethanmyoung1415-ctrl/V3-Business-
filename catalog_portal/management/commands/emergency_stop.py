from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from catalog_portal import emergency

class Command(BaseCommand):
    help="Enable or clear the LOCAL preproduction emergency stop"
    def add_arguments(self,parser):
        group=parser.add_mutually_exclusive_group()
        group.add_argument("--enable",action="store_true")
        group.add_argument("--disable",action="store_true")
    def handle(self,*args,**options):
        if not getattr(settings,"LOCAL_DEV",False):
            raise CommandError("Emergency file control is local-development only")
        if options["enable"]:
            result=emergency.set_paused(True)
        elif options["disable"]:
            result=emergency.set_paused(False)
        else:
            result={"paused":emergency.is_paused()}
        self.stdout.write("V3 paused: "+str(result["paused"]))
