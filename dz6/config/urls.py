from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

from qna import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('hot/', views.index, {'variant': 'hot'}, name='hot'),
    path('question/add/', views.ask, name='ask'),
    path('question/<int:pk>/answer/add/', views.add_answer, name='add-answer'),
    path('question/answer/<int:pk>/vote/', csrf_exempt(views.answer_vote), name='answer-vote'),
    path('question/answer/<int:pk>/correct/', csrf_exempt(views.answer_correct), name='answer-correct'),
    path('question/<int:pk>/vote/', csrf_exempt(views.question_vote), name='question-vote'),
    path('question/<int:pk>/', views.question_view, name='question-detail'),
    path('question/<int:pk>/edit/', views.QuestionUpdate.as_view(), name='question-update'),
    path('signup/', views.user_signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('settings/', views.user_settings, name='settings'),
    path('search/', views.search, name='search'),
    path('tag/<str:tag>/', views.tag_search, name='tag'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
