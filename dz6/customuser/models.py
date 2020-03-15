from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from customuser.user import User
from customuser.forms import SignUpForm, LoginForm, SettingsForm


class UserSignup(View):
    template = 'customuser/signup.html'

    def get(self, request):
        form = SignUpForm()
        return render(request, self.template, {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('index')
        return render(request, self.template, {'form': form})


class UserLogin(View):
    template = 'customuser/login.html'

    def get(self, request):
        form = LoginForm()
        return render(request, self.template, {'form': form})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return redirect('index')
            else:
                return HttpResponse("403")
        else:
            form = LoginForm(request)
            return render(request, self.template,
                          {'form': form, 'errors': form.get_invalid_login_error().message})


class UserLogout(View):
    def get(self, request):
        logout(request)
        return redirect('index')


class UserSettings(View):
    template = 'customuser/settings.html'

    @login_required
    def get(self, request):
        form = SettingsForm(instance=request.user)
        return render(request, self.template, {'form': form})

    @login_required
    def post(self, request):
        form = SettingsForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('settings')
        return render(request, self.template, {'form': form})
