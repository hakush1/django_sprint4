from datetime import timedelta
from pathlib import Path
from shutil import rmtree
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import requests
from bs4 import BeautifulSoup

from blog.models import Category, Comment, Location, Post

User = get_user_model()

HABR_POSTS = [
    {
        'title': 'Cloud.ru: как выбирать архитектуру форм в React/Angular',
        'text': (
            'Когда форма разрастается до десятков полей, быстро становится '
            'видно, что главная проблема не в кнопках и инпутах, а в логике. '
            'Хорошая практика - отделять слой UI от доменных правил: проверки '
            'бизнес-ограничений, преобразование значений и реакции на ошибки '
            'должны жить отдельно от разметки. Если правила описаны явно, '
            'команда быстрее добавляет новые поля, а изменение одного '
            'сценария '
            'не ломает остальные.'
        ),
        'article_url': (
            'https://habr.com/ru/companies/cloud_x/articles/1004508/'
        ),
        'image_url': (
            'https://habrastorage.org/getpro/habr/upload_files/b3f/905/eba/'
            'b3f905eba7520e054de04ea90494997e.jpg'
        ),
        'category': 'frontend',
        'location': 'Москва',
        'author': 'maksim',
        'days_ago': 1,
    },
    {
        'title': 'Selectel: ML-дайджест недели без шума',
        'text': (
            'На неделе особенно обсуждали практичность AI-агентов, стоимость '
            'инференса и безопасность пайплайнов. Важно смотреть не только на '
            'качество ответов модели, но и на задержки, цену одного запроса и '
            'предсказуемость результата в проде. Отдельный акцент на том, что '
            'без мониторинга и ограничений доступа даже сильная модель быстро '
            'становится риском для бизнеса.'
        ),
        'article_url': (
            'https://habr.com/ru/companies/selectel/articles/1004450/'
        ),
        'image_url': (
            'https://habrastorage.org/getpro/habr/upload_files/800/16a/ba2/'
            '80016aba2c88061ed9c923a284ccf3d5.jpeg'
        ),
        'category': 'ai-ml',
        'location': 'Санкт-Петербург',
        'author': 'olga',
        'days_ago': 2,
    },
    {
        'title': 'Samsung: что умеют современные смарт-часы',
        'text': (
            'Смарт-часы давно вышли за рамки шагомера и уведомлений. Сейчас '
            'ключевая ценность - связка датчиков, которая помогает оценивать '
            'сон, нагрузку и восстановление по косвенным метрикам. Но данные '
            'с запястья не заменяют медицинскую диагностику: тренды полезны '
            'для повседневных решений, а выводы стоит проверять в контексте '
            'состояния человека и образа жизни.'
        ),
        'article_url': (
            'https://habr.com/ru/companies/samsung/articles/1004510/'
        ),
        'image_url': (
            'https://habrastorage.org/getpro/habr/upload_files/a59/2ef/1f9/'
            'a592ef1f951dd64df97cc77a3ec9abea.png'
        ),
        'category': 'gadgets',
        'location': 'Казань',
        'author': 'marta',
        'days_ago': 3,
    },
]


class Command(BaseCommand):
    help = 'Заполняет Блогикум качественными демо-данными.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Не очищать существующие данные перед заполнением.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        keep_existing = options['keep']
        if not keep_existing:
            self._clear_data()

        users = self._create_users()
        categories = self._create_categories()
        locations = self._create_locations()
        posts = self._create_posts(users, categories, locations)
        self._create_comments(posts, users)

        self.stdout.write(self.style.SUCCESS('Демо-данные успешно заполнены.'))
        self.stdout.write(
            'Аккаунты: admin/admin12345, marta/marta12345, '
            'maksim/maksim12345, olga/olga12345'
        )

    def _clear_data(self):
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Category.objects.all().delete()
        Location.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        media_dir = Path(settings.MEDIA_ROOT)
        posts_images_dir = media_dir / 'posts_images'
        if posts_images_dir.exists():
            rmtree(posts_images_dir)

    def _create_users(self):
        return {
            'admin': self._create_user(
                username='admin',
                password='admin12345',
                first_name='Марина',
                last_name='Администратор',
                email='admin@blogicum.local',
                is_staff=True,
                is_superuser=True,
            ),
            'marta': self._create_user(
                username='marta',
                password='marta12345',
                first_name='Марта',
                last_name='Лебедева',
                email='marta@blogicum.local',
            ),
            'maksim': self._create_user(
                username='maksim',
                password='maksim12345',
                first_name='Максим',
                last_name='Орлов',
                email='maksim@blogicum.local',
            ),
            'olga': self._create_user(
                username='olga',
                password='olga12345',
                first_name='Ольга',
                last_name='Смирнова',
                email='olga@blogicum.local',
            ),
        }

    def _create_categories(self):
        return {
            'frontend': self._get_category(
                'frontend',
                'Frontend',
                'Обсуждение интерфейсов, форм и UX-практик.',
            ),
            'ai-ml': self._get_category(
                'ai-ml',
                'AI & ML',
                'Новости и практика машинного обучения.',
            ),
            'gadgets': self._get_category(
                'gadgets',
                'Гаджеты',
                'Технологичные устройства и прикладные сценарии.',
            ),
            'career': self._get_category(
                'career',
                'Карьера',
                'Работа в IT, развитие навыков и рост команды.',
            ),
        }

    def _create_locations(self):
        return {
            'Москва': self._get_location('Москва'),
            'Санкт-Петербург': self._get_location('Санкт-Петербург'),
            'Казань': self._get_location('Казань'),
            'Екатеринбург': self._get_location('Екатеринбург'),
            'Новосибирск': self._get_location('Новосибирск'),
        }

    def _create_posts(self, users, categories, locations):
        now = timezone.now()
        posts_data = list(HABR_POSTS)
        posts_data.extend(
            [
                {
                    'title': 'Как провести ревью без токсичности',
                    'text': (
                        'Хорошее ревью не про «найти виноватого», а про '
                        'снижение рисков. Сначала проверяем поведение и '
                        'регрессии, потом стиль. И всегда объясняем '
                        'причину замечания.'
                    ),
                    'category': 'career',
                    'location': 'Екатеринбург',
                    'author': 'marta',
                    'days_ago': 4,
                },
                {
                    'title': (
                        'Пять ошибок в пагинации, которые бесят '
                        'пользователей'
                    ),
                    'text': (
                        'Основные проблемы: нет первого/последнего шага, '
                        'ломается сохранение фильтров в URL и непонятно, '
                        'сколько всего страниц. Исправление занимает час, '
                        'эффект на UX — огромный.'
                    ),
                    'category': 'frontend',
                    'location': 'Новосибирск',
                    'author': 'maksim',
                    'days_ago': 5,
                },
                {
                    'title': 'Нормальная база комментариев: что важно заранее',
                    'text': (
                        'Если заранее продумать связи post-author-created_at, '
                        'редактирование и удаление комментариев добавляются '
                        'быстро и без боли. Сложности обычно в правах, а не в '
                        'CRUD.'
                    ),
                    'category': 'ai-ml',
                    'location': 'Москва',
                    'author': 'olga',
                    'days_ago': 6,
                },
                {
                    'title': 'Пост с отложенной датой для проверки логики',
                    'text': (
                        'Этот пост появится для остальных пользователей '
                        'после наступления даты публикации, но автор видит '
                        'его сразу в своём профиле.'
                    ),
                    'category': 'career',
                    'location': 'Санкт-Петербург',
                    'author': 'maksim',
                    'days_ago': -1,
                },
                {
                    'title': 'Скрытый пост для проверки прав доступа',
                    'text': (
                        'Пост снят с публикации и должен быть доступен '
                        'только автору, но не другим пользователям.'
                    ),
                    'category': 'frontend',
                    'location': 'Казань',
                    'author': 'marta',
                    'days_ago': 7,
                    'is_published': False,
                },
            ]
        )

        created_posts = []
        for index, post_data in enumerate(posts_data, start=1):
            pub_date = now - timedelta(days=post_data['days_ago'])
            post = Post.objects.create(
                title=post_data['title'],
                text=post_data['text'],
                pub_date=pub_date,
                author=users[post_data['author']],
                category=categories[post_data['category']],
                location=locations[post_data['location']],
                is_published=post_data.get('is_published', True),
            )
            image_url = post_data.get('image_url')
            article_url = post_data.get('article_url')
            if not image_url and article_url:
                image_url = self._extract_og_image(article_url)
            if image_url:
                self._attach_remote_image(post, image_url, index)
            created_posts.append(post)
        return created_posts

    def _create_comments(self, posts, users):
        for index, post in enumerate(posts[:7], start=1):
            Comment.objects.create(
                post=post,
                author=users['marta'],
                text=(
                    f'Спасибо за материал #{index}. Особенно понравилось, '
                    'что выводы можно применить на практике.'
                ),
            )
            Comment.objects.create(
                post=post,
                author=users['maksim'],
                text=(
                    f'Добавил бы в пост #{index} больше примеров из '
                    'продуктовых сценариев, но в целом разобрано отлично.'
                ),
            )
            Comment.objects.create(
                post=post,
                author=users['olga'],
                text=(
                    f'По посту #{index} есть вопрос: как это масштабируется '
                    'в команде из 10+ разработчиков?'
                ),
            )

    @staticmethod
    def _attach_remote_image(post, image_url, index):
        headers = {'User-Agent': 'Mozilla/5.0'}
        content = None
        try:
            request = Request(image_url, headers=headers)
            with urlopen(request, timeout=20) as response:
                content = response.read()
        except (HTTPError, URLError, TimeoutError):
            pass

        if content is None:
            logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo.png'
            if logo_path.exists():
                content = logo_path.read_bytes()
                ext = 'png'
            else:
                return
        else:
            ext = image_url.split('?')[0].rsplit('.', 1)[-1].lower()
            if ext not in {'jpg', 'jpeg', 'png', 'webp'}:
                ext = 'jpg'

        filename = f'habr_post_{index}.{ext}'
        post.image.save(filename, ContentFile(content), save=True)

    @staticmethod
    def _extract_og_image(article_url):
        try:
            response = requests.get(
                article_url,
                timeout=20,
                headers={'User-Agent': 'Mozilla/5.0'},
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        meta = soup.find('meta', property='og:image')
        if not meta:
            return None
        return meta.get('content')

    @staticmethod
    def _create_user(username, password, **extra_fields):
        user, _ = User.objects.get_or_create(username=username)
        for key, value in extra_fields.items():
            setattr(user, key, value)
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def _get_category(slug, title, description):
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={
                'title': title,
                'description': description,
                'is_published': True,
            },
        )
        return category

    @staticmethod
    def _get_location(name):
        location, _ = Location.objects.get_or_create(
            name=name,
            defaults={'is_published': True},
        )
        return location
