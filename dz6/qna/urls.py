from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from qna.views import QuestionView, QuestionUpdate, AnswerView, AnswerVoteView, AnswerCorrectView, QuestionVoteView, \
    SearchView

urlpatterns = [
    path('question/add/', QuestionView.as_view(), name='ask'),
    path('question/<int:pk>/answer/add/', AnswerView.as_view(), name='add-answer'),
    path('question/answer/<int:pk>/vote/', csrf_exempt(AnswerVoteView.as_view()), name='answer-vote'),
    path('question/answer/<int:pk>/correct/', csrf_exempt(AnswerCorrectView.as_view()), name='answer-correct'),
    path('question/<int:pk>/vote/', csrf_exempt(QuestionVoteView.as_view()), name='question-vote'),
    path('question/<int:pk>/', QuestionView.as_view(), name='question-detail'),
    path('question/<int:pk>/edit/', QuestionUpdate.as_view(), name='question-update'),
    path('search/', SearchView.as_view(), name='search'),
]
