from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = (
        'Запускает проект одной командой: migrate, seed_demo, runserver.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--addrport',
            default='127.0.0.1:8000',
            help='Адрес и порт для runserver, по умолчанию 127.0.0.1:8000.',
        )
        parser.add_argument(
            '--keep-data',
            action='store_true',
            help='Не очищать и не пересоздавать демо-данные.',
        )

    def handle(self, *args, **options):
        addrport = options['addrport']
        keep_data = options['keep_data']

        self.stdout.write(self.style.NOTICE('Применяю миграции...'))
        call_command('migrate')

        if not keep_data:
            self.stdout.write(self.style.NOTICE('Заполняю демо-данные...'))
            call_command('seed_demo')
        else:
            self.stdout.write(
                self.style.NOTICE('Демо-данные сохранены без изменений.')
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Сервер запущен: http://{addrport}/ '
                '(Ctrl+C для остановки).'
            )
        )
        call_command('runserver', addrport)
