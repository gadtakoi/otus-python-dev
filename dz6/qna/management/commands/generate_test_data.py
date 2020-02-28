from django.core.management.base import BaseCommand
from faker import Faker
from random import randint

from qna.models import User, Tag, Question, Answer


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.create_users(30)
        self.create_tags(10)
        self.create_q(100)
        self.create_a(100 * 10)

    def create_users(self, amount: int):
        fake = Faker(['ru_RU', 'en_NZ', 'de_DE', 'es_MX', 'fr_FR', 'fi_FI'])

        for _ in range(amount):
            username = fake.user_name()
            name = fake.name().split()
            first_name = name[0]
            last_name = name[1]
            email = fake.email()
            password = 12345
            user = User.objects.create_user(username, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = True
            user.save()

    def create_tags(self, amount: int):
        fake = Faker()
        for _ in range(amount):
            t = Tag()
            word = fake.word()
            t.name = word
            t.save()

    def create_q(self, amount: int):
        fake = Faker()
        for _ in range(amount):
            q = Question()
            q.title = fake.paragraph(nb_sentences=3, variable_nb_sentences=True, ext_word_list=None)[:254]
            q.content = fake.texts(nb_texts=3, max_nb_chars=400, ext_word_list=None)[0]
            q.author = User.objects.order_by("?").first()
            q.vote_count = randint(1, 1000)
            q.save()
            tags = Tag.objects.values_list('id', flat=True).order_by("?")[:randint(0, 3)]
            q.tags.add(*list(tags))
            q.save()

    def create_a(self, amount: int):
        fake = Faker()
        for _ in range(amount):
            a = Answer()
            a.content = fake.texts(nb_texts=3, max_nb_chars=400, ext_word_list=None)[0]
            a.author = User.objects.order_by("?").first()
            a.question = Question.objects.order_by("?").first()
            a.vote_count = randint(1, 1000)
            a.save()
