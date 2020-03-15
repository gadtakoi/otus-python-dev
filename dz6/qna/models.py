from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings
from django.db import models
from django.urls import reverse

from config.settings import ANSWERS_PER_PAGE


class Question(models.Model):
    objects = models.Manager()

    title = models.CharField(verbose_name='Заголовок', max_length=255, null=False, blank=False)
    content = models.TextField(verbose_name='Содержание', null=False, blank=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    date_create = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    tags = models.ManyToManyField('qna.Tag', verbose_name='Теги', blank=True)
    vote_count = models.IntegerField(verbose_name='Голоса', default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('question-detail', kwargs={'pk': self.pk})

    def answers(self) -> int:
        answers_list = self.answer_set.all().order_by('-vote_count', '-date_create')
        paginator = Paginator(answers_list, ANSWERS_PER_PAGE)
        try:
            answers = paginator.page(self.page_num)
        except PageNotAnInteger:
            answers = paginator.page(1)
        except EmptyPage:
            answers = paginator.page(paginator.num_pages)

        return answers

    def show_tags(self):
        return self.tags.all()

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['-date_create']


class Answer(models.Model):
    objects = models.Manager()

    question = models.ForeignKey(to='qna.Question', verbose_name='Вопрос', on_delete=models.CASCADE)
    content = models.TextField(verbose_name='Содержание', null=False, blank=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    date_create = models.DateTimeField(verbose_name='Дата написания', auto_now_add=True)
    vote_count = models.IntegerField(verbose_name='Голоса', default=0)

    correct = models.BooleanField(verbose_name='Правильный ответ', default=False)
    sent = models.BooleanField(verbose_name='Письмо отправлено', default=False)

    def __str__(self):
        return self.content[:40]

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        ordering = ['date_create']


class Tag(models.Model):
    objects = models.Manager()

    name = models.CharField(verbose_name="Имя", unique=True, max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"


class Vote(models.Model):
    objects = models.Manager()

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Автор')
    value = models.SmallIntegerField(verbose_name='Голос', default=0, help_text='-1, 0, 1')

    question = models.ForeignKey(to='qna.Question',
                                 verbose_name='Вопрос',
                                 on_delete=models.CASCADE,
                                 null=True,
                                 blank=True)
    answer = models.ForeignKey(to='qna.Answer',
                               verbose_name='Ответ',
                               on_delete=models.CASCADE,
                               null=True,
                               blank=True)

    date_create = models.DateTimeField(verbose_name='Дата написания', auto_now_add=True)

    def __str__(self):
        return "{} - {}".format(self.author, self.value)

    class Meta:
        verbose_name = 'Голос'
        verbose_name_plural = 'Голоса'
        ordering = ['date_create']
