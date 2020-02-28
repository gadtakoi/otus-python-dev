from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import UpdateView

from config.settings import SEARCH_PER_PAGE, INDEX_PER_PAGE, TAG_PER_PAGE
from qna.forms import QuestionForm, SignUpForm, LoginForm, SettingsForm, AnswerForm
from qna.models import Question, Answer, Vote
from qna.utils import send_email_answer_alert


def index(request, **kwargs):
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


@login_required
def ask(request):
    q = Question(author=request.user)
    form = QuestionForm(request.POST, instance=q)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(f"/question/{q.id}/")
    return render(request, 'qna/question_form.html')


def question_view(request, pk):
    q = Question.objects.get(pk=pk)
    q.page_num = int(request.GET.get('page', 1))
    return render(request, 'qna/question_view.html', {'question': q})


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


def user_signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'qna/signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return redirect('index')
            else:
                return HttpResponse("403!!!")
        else:
            form = LoginForm(request)
            return render(request, 'qna/login.html', {'form': form, 'errors': form.get_invalid_login_error().message})

    else:
        form = LoginForm()
        return render(request, 'qna/login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('index')


@login_required
def user_settings(request):
    if request.method == 'POST':
        form = SettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('settings')
    else:
        form = SettingsForm(instance=request.user)
    return render(request, 'qna/settings.html', {'form': form})


def search(request):
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


def tag_search(request, **kwargs):
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


@login_required
def add_answer(request, **kwargs):
    question_id = kwargs.get('pk', '')
    form = AnswerForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        if question_id:
            obj.question_id = question_id
            obj.author = request.user
            obj.save()
            send_email_answer_alert(question_id, request)
    return HttpResponseRedirect(f"/question/{question_id}/")


@login_required
def question_vote(request, **kwargs):
    _id = kwargs.get('pk', '')
    out = _vote_changer(Question, _id, request)
    return JsonResponse(out)


@login_required
def answer_vote(request, **kwargs):
    _id = kwargs.get('pk', '')
    out = _vote_changer(Answer, _id, request)
    return JsonResponse(out)


def _vote_changer(cls, pk: str, request):
    object_id = pk
    v = request.GET.get('v', '')
    out = {'state': 'error'}
    if object_id and v:
        instance = cls.objects.get(id=int(object_id))
        allow_to_vote = _vote_processing(request, instance, v)
        if allow_to_vote:
            if v == 'down':
                instance.vote_count -= 1
            elif v == 'up':
                instance.vote_count += 1
            instance.save()
            out = {'state': 'ok'}
    return out


def _vote_processing(request, obj, v: str) -> bool:
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


@login_required
def answer_correct(request, **kwargs):
    answer_id = int(kwargs.get('pk', ''))
    answer = Answer.objects.get(id=answer_id)
    if answer.question.author == request.user:
        Answer.objects.filter(question__id=answer.question.id).update(correct=False)
        answer.correct = True
        answer.save()
        out = {'state': 'ok', 'answer_id': answer.id}
    else:
        out = {'state': 'error'}

    return JsonResponse(out)
