from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import UpdateView

from config.settings import SEARCH_PER_PAGE, INDEX_PER_PAGE, TAG_PER_PAGE
from qna.forms import QuestionForm, AnswerForm
from qna.models import Question, Answer, Vote
from qna.utils import send_email_answer_alert


class IndexView(View):
    def get(self, request, **kwargs):
        variant = kwargs.get('variant', '')
        page_num = request.GET.get('page', 1)
        if variant == 'hot':
            questions_list = Question.objects.all().order_by('-vote_count', '-date_create')
        else:
            questions_list = Question.objects.all().order_by('-date_create')

        paginator = Paginator(questions_list, INDEX_PER_PAGE)

        try:
            questions = paginator.page(page_num)
        except PageNotAnInteger:
            questions = paginator.page(1)
        except EmptyPage:
            questions = paginator.page(paginator.num_pages)

        context = {
            'questions': questions,
            'variant': variant
        }

        return render(request, 'qna/index.html', context)


class AskView(View):
    @method_decorator(login_required)
    def post(self, request):
        q = Question(author=request.user)
        form = QuestionForm(request.POST, instance=q)
        if form.is_valid():
            form.save()
            return redirect(q)
        return render(request, 'qna/question_form.html')


class QuestionView(View):
    def get(self, request, pk):
        q = Question.objects.get(pk=pk)
        q.page_num = int(request.GET.get('page', 1))
        return render(request, 'qna/question_view.html', {'question': q})


class SearchView(View):
    def get(self, request):
        q = request.GET.get('q', '')
        tail = "&q={}".format(q)

        if q and q.startswith('tag:'):
            return redirect(to=reverse('tag', kwargs={'tag': q[4:]}))
        elif q:
            questions_list = Question.objects.filter(Q(title__icontains=q) | Q(content__icontains=q)). \
                order_by('-vote_count', '-date_create')

            paginator = Paginator(questions_list, SEARCH_PER_PAGE)
            page_num = int(request.GET.get('page', 1))
            try:
                questions = paginator.page(page_num)
            except PageNotAnInteger:
                questions = paginator.page(1)
            except EmptyPage:
                questions = paginator.page(paginator.num_pages)
        else:
            questions = ''

        return render(request, 'qna/search.html', {'questions': questions, 'q': q, 'tail': tail})


class TagSearchView(View):
    def get(self, request, **kwargs):
        tag = kwargs['tag']

        if tag:
            questions_list = Question.objects.filter(tags__name__icontains=tag).order_by('-vote_count', '-date_create')
            paginator = Paginator(questions_list, TAG_PER_PAGE)
            page_num = int(request.GET.get('page', 1))
            try:
                questions = paginator.page(page_num)
            except PageNotAnInteger:
                questions = paginator.page(1)
            except EmptyPage:
                questions = paginator.page(paginator.num_pages)

        return render(request, 'qna/tag.html', {'questions': questions, 'q': 'tag:{}'.format(tag)})


class QuestionUpdate(UpdateView):
    model = Question
    fields = ['title', 'content', 'tags']
    template_name_suffix = '_form'

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.author != self.request.user:
            return redirect(obj)
        return super(QuestionUpdate, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tags'] = (context['question'].tags.all().values_list(flat=True))
        return context


class AnswerView(View):
    @method_decorator(login_required)
    def post(self, request, **kwargs):
        question_id = kwargs.get('pk', '')
        form = AnswerForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if question_id:
                obj.question_id = question_id
                obj.author = request.user
                obj.save()
                sent = send_email_answer_alert(question_id, request)
                if sent:
                    obj.sent = True
                    obj.save()

        return HttpResponseRedirect(f"/question/{question_id}/")


class AnswerCorrectView(View):
    def post(self, request, pk):
        if request.user.is_authenticated:
            answer_id = int(pk)
            answer = Answer.objects.get(id=answer_id)
            if answer.question.author == request.user:
                Answer.objects.filter(question__id=answer.question.id).update(correct=False)
                answer.correct = True
                answer.save()
                out = {'state': 'ok', 'answer_id': answer.id}
            else:
                out = {'state': 'error'}
            return JsonResponse(out)
        else:
            return HttpResponseForbidden()


class VoteChanger:
    def _vote_changer(self, cls, pk: str, request):
        object_id = pk
        v = request.GET.get('v', '')
        out = {'state': 'error'}
        if object_id and v:
            instance = cls.objects.get(id=int(object_id))
            allow_to_vote = self._vote_processing(request, instance, v)
            if allow_to_vote:
                if v == 'down':
                    instance.vote_count -= 1
                elif v == 'up':
                    instance.vote_count += 1
                instance.save()
                out = {'state': 'ok'}
        return out

    def _vote_processing(self, request, obj, v: str) -> bool:
        allow_to_vote = False

        if v == 'up':
            sign = 1
        else:
            sign = -1
        new_vote = {'author': request.user, 'value': sign}
        try:
            if isinstance(obj, Question):
                new_vote['question'] = obj
                vote = Vote.objects.get(author=request.user, question=obj)
                if vote.value != sign:
                    vote.value += sign
                    vote.save()
                    allow_to_vote = True
            elif isinstance(obj, Answer):
                new_vote['answer'] = obj
                vote = Vote.objects.get(author=request.user, answer=obj)
                if vote.value != sign:
                    vote.value += sign
                    vote.save()
                    allow_to_vote = True
        except ObjectDoesNotExist:
            vote = Vote(**new_vote)
            vote.save()
            allow_to_vote = True
        return allow_to_vote


class QuestionVoteView(View, VoteChanger):
    def post(self, request, pk):
        if request.user.is_authenticated:
            out = self._vote_changer(Question, pk, request)
            return JsonResponse(out)
        else:
            return HttpResponseForbidden()


class AnswerVoteView(View, VoteChanger):
    def post(self, request, pk):
        if request.user.is_authenticated:
            out = self._vote_changer(Answer, pk, request)
            return JsonResponse(out)
        else:
            return HttpResponseForbidden()
