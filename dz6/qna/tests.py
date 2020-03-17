import datetime
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from customuser.models import User
from qna.models import Question, Answer, Tag
from qna.views import QuestionVoteView, AnswerVoteView, AnswerCorrectView


def create_question(author, title='Test question', content='Test question content'):
    return Question.objects.create(title=title, content=content, author=author)


def create_answer(question, author, content='Test answer content'):
    return Answer.objects.create(content=content, question=question, author=author)


def create_tag(name):
    return Tag.objects.get_or_create(name=name)[0]


class IndexViewTests(TestCase):
    questions_data = {
        'question1': {'content': 'content1', 'vote_count': 3, 'days': 0},
        'question2': {'content': 'content2', 'vote_count': 3, 'days': 1},
        'question3': {'content': 'content3', 'vote_count': 2, 'days': 2},
        'question4': {'content': 'content4', 'vote_count': 1, 'days': 3},
    }

    def setUp(self):
        question_author = User.objects.create_user(
            username='username1', email='username1@eamil.com', password='password'
        )

        for title, data in self.questions_data.items():
            pub_date = timezone.now() + datetime.timedelta(days=data['days'])
            question = Question.objects.create(
                title=title,
                content=data['content'],
                vote_count=data['vote_count'],
                author=question_author,
            )
            question.pub_date = pub_date
            question.save()

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_questions_sorted_by_pub_date(self):
        response = self.client.get(reverse('index'))
        self.assertQuerysetEqual(
            response.context['questions'],
            ['<Question: question4>', '<Question: question3>', '<Question: question2>', '<Question: question1>']
        )

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_questions_sorted_by_rating_and_pub_date(self):
        response = self.client.get(reverse('hot'))
        self.assertQuerysetEqual(
            response.context['questions'],
            ['<Question: question2>', '<Question: question1>', '<Question: question3>', '<Question: question4>']
        )


class SearchViewTests(TestCase):
    questions_data = {
        'question1': 'content1',
        'question2': 'content12',
        'question3': 'content3',
    }
    tags_data = {
        'question1': ('tag1', 'tag2'),
        'question2': ('tag3',),
        'question3': ('tag1',),
    }

    def setUp(self):
        question_author = User.objects.create_user(
            username='username1', email='username1@gmail.com', password='password'
        )

        for title, content in self.questions_data.items():
            question = Question.objects.create(title=title, content=content, author=question_author)
            question.save(self.tags_data[title])

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_empty_search(self):
        response = self.client.get(reverse('search') + '?q=question4')
        self.assertContains(response, 'question4 not found')
        self.assertQuerysetEqual(response.context['questions'], [])

    def test_empty_search_by_tag(self):
        response = self.client.get(reverse('tag', args=('tag5',)))
        self.assertContains(response, 'tag5 not found')
        self.assertQuerysetEqual(response.context['questions'], [])

    def test_search_by_title(self):
        response = self.client.get(reverse('search') + '?q=question1')
        self.assertQuerysetEqual(response.context['questions'], ['<Question: question1>'])

    def test_search_by_content(self):
        response = self.client.get(reverse('search') + '?q=content1')
        self.assertQuerysetEqual(response.context['questions'], ['<Question: question2>', '<Question: question1>'])

    def test_search_by_tag(self):
        response = self.client.get(reverse('tag', args=('tag1',)))
        self.assertQuerysetEqual(response.context['questions'], ['<Question: question3>', '<Question: question1>'])


class AnswerVoteViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.question_author = User.objects.create_user(
            username='username1', email='username1@gmail.com', password='password'
        )
        self.answer_author = User.objects.create_user(
            username='username2', email='username2@gmail.com', password='password'
        )
        self.question = create_question(author=self.question_author)
        self.answer = create_answer(author=self.answer_author, question=self.question)

    def test_unauthorized_user_can_not_set_correct_answer(self):
        response = self.client.post(self.answer.get_correct_url())
        self.assertEqual(response.status_code, 403)

    def test_not_question_author_can_not_set_correct_answer(self):
        request = self.factory.post(self.answer.get_correct_url())
        request.user = self.answer_author
        response = AnswerCorrectView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)

    def test_question_author_can_set_correct_answer(self):
        request = self.factory.post(self.answer.get_correct_url())
        request.user = self.question_author
        response = AnswerCorrectView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)


class VoteViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.question_author = User.objects.create_user(
            username='username1', email='username1@gmail.com', password='password'
        )
        self.answer_author = User.objects.create_user(
            username='username2', email='username2@gmail.com', password='password'
        )
        self.question = create_question(author=self.question_author)
        self.answer = create_answer(author=self.answer_author, question=self.question)

    def test_unauthorized_user_can_not_vote_for_question(self):
        response = self.client.post(self.question.get_vote_url())
        self.assertEqual(response.status_code, 403)

    def test_unauthorized_user_can_not_for_vote_for_answer(self):
        response = self.client.post(self.answer.get_vote_url())
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_can_do_only_one_question_vote_up(self):
        request = self.factory.post(self.question.get_vote_url() + "?v=up")
        request.user = self.answer_author

        self.assertEqual(self.question.vote_count, 0)

        response = QuestionVoteView.as_view()(request, self.question.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, 1)

        response = QuestionVoteView.as_view()(request, self.question.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, 1)

    def test_authorized_user_can_do_only_one_question_vote_down(self):
        request = self.factory.post(self.question.get_vote_url() + '?v=down')
        request.user = self.answer_author

        self.assertEqual(self.question.vote_count, 0)

        response = QuestionVoteView.as_view()(request, self.question.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, -1)

        response = QuestionVoteView.as_view()(request, self.question.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, -1)

    def test_authorized_user_can_do_question_vote_toggle(self):
        request_up = self.factory.post(self.question.get_vote_url() + '?v=up')
        request_down = self.factory.post(self.question.get_vote_url() + '?v=down')

        request_up.user = self.answer_author
        request_down.user = self.answer_author

        self.assertEqual(self.question.vote_count, 0)

        QuestionVoteView.as_view()(request_up, self.question.pk)
        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, 1)

        QuestionVoteView.as_view()(request_down, self.question.pk)
        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, 0)

        QuestionVoteView.as_view()(request_down, self.question.pk)
        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, -1)

        QuestionVoteView.as_view()(request_up, self.question.pk)
        self.assertEqual(Question.objects.get(pk=self.question.pk).vote_count, 0)

    def test_authorized_user_can_do_only_one_answer_vote_up(self):
        request = self.factory.post(self.answer.get_vote_url() + '?v=up')

        request.user = self.question_author

        self.assertEqual(self.answer.vote_count, 0)

        response = AnswerVoteView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, 1)

        response = AnswerVoteView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, 1)

    def test_authorized_user_can_do_only_one_answer_vote_down(self):
        request = self.factory.post(self.answer.get_vote_url() + '?v=down')

        request.user = self.question_author

        self.assertEqual(self.answer.vote_count, 0)

        response = AnswerVoteView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, -1)

        response = AnswerVoteView.as_view()(request, self.answer.pk)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, -1)

    def test_authorized_user_can_do_answer_vote_toggle(self):
        request_up = self.factory.post(self.answer.get_vote_url() + '?v=up')
        request_down = self.factory.post(self.answer.get_vote_url() + '?v=down')

        request_up.user = self.question_author
        request_down.user = self.question_author

        self.assertEqual(self.answer.vote_count, 0)

        AnswerVoteView.as_view()(request_up, self.answer.pk)
        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, 1)

        AnswerVoteView.as_view()(request_down, self.answer.pk)
        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, 0)

        AnswerVoteView.as_view()(request_down, self.answer.pk)
        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, -1)

        AnswerVoteView.as_view()(request_up, self.answer.pk)
        self.assertEqual(Answer.objects.get(pk=self.answer.pk).vote_count, 0)
