from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms

from qna.models import Question, User, Answer


class QuestionForm(ModelForm):
    class Meta:
        model = Question
        fields = ('title', 'content', 'tags')


class AnswerForm(ModelForm):
    class Meta:
        model = Answer
        fields = ('content',)


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'avatar')

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']
        try:
            main, sub = avatar.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError('Please use a JPEG, GIF or PNG image.')

        except AttributeError:
            pass

        return avatar


class SettingsForm(forms.ModelForm):
    username = forms.CharField(disabled=True, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'avatar')


class LoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ('username', 'password')
