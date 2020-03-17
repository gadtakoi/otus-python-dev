from django.urls import path

from customuser.views import UserSignup, UserLogin, UserLogout, UserSettings
from qna import views
from qna.views import QuestionView

urlpatterns = [
    path('signup/', UserSignup.as_view(), name='signup'),
    path('login/', UserLogin.as_view(), name='login'),
    path('logout/', UserLogout.as_view(), name='logout'),
    path('settings/', UserSettings.as_view(), name='settings'),
]
