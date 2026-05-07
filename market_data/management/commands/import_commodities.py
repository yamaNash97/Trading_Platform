from django.core.management.base import BaseCommand, CommandError

from market_data.services import COMMODITY_DEFINITIONS, import_alpha_vantage_commodity


class Command(BaseCommand):
    help = 'Import Alpha Vantage commodity history into PriceData.'

    def add_arguments(self, parser):
        parser.add_argument(
            'symbols',
            nargs='*',
            help='Commodity symbols to import. Defaults to WTI GOLD NATURAL_GAS.',
        )

    def handle(self, *args, **options):
        symbols = options['symbols'] or ['WTI', 'GOLD', 'NATURAL_GAS']
        unsupported = [symbol for symbol in symbols if symbol.upper() not in COMMODITY_DEFINITIONS]
        if unsupported:
            raise CommandError(f'Unsupported commodities: {", ".join(unsupported)}')

        for symbol in symbols:
            stock, imported = import_alpha_vantage_commodity(symbol)
            self.stdout.write(self.style.SUCCESS(f'{stock.symbol}: imported {imported} new rows.'))
