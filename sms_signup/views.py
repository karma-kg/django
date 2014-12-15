# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic.base import View
from django.contrib import auth, messages
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.utils.timezone import utc
from django.core.urlresolvers import reverse

from nexmomessage import NexmoMessage

from .forms import RegistrationForm, ActivationForm, LoginForm
from .models import ActivationSMSCode
from .backend import SMSAuthBackend

from random_words import RandomWords

import datetime
from datetime import timedelta


ACTIVATION_ALREADY_HAS_BEEN = _(u'Активация уже производилась')
WRONG_ACTIVATION_CODE = _(u'Неверный код активации')
ACTIVATION_PERIOD_EXPIRED = _(u'Истек период активации')
LOGIN_ERROR = _(u'При входе возникла ошибка')
SEND_MESSAGE_ERROR = _(u'Ошибка при попытке отправки сообщения')
ACCOUNT_ACTIVATED = _(u"Ваш аккаунт был активирован. Спасибо, за регистрацию")
ACTIVATION_PERIOD = 2 # days
NEXMO_API_KEY ='5214868e'
NEXMO_SECRET_KEY = '75fbcd18'

class RegistrationView(View):

    """
    User registration
    """

    form_class = RegistrationForm
    template_name = 'sms_signup/signup.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial={})
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['username']
            # Genarates the random word for the sms code
            random_word = RandomWords()
            sms_code = random_word.random_word()

            # Creates the record with the random 
            # activation word and the phone number
            ActivationSMSCode.objects.create(
                sms_code=sms_code,
                phone=phone,
                sms_code_init_time=datetime.datetime.utcnow().replace(
                    tzinfo=utc)
            )

            try:
                msg = {
                        'reqtype': 'json',
                        'api_key': NEXMO_API_KEY,
                        'api_secret': NEXMO_SECRET_KEY,
                        'from': 'moZan',
                        'to': phone,
                        'text': sms_cod,
                    }
                sms = NexmoMessage(msg)
                sms.set_text_info(msg['text'])

                # Sends sms message with the random word
                sms.send_request()

            except Exception, e:
                messages.add_message(
                    request,
                    messages.ERROR,
                    SEND_MESSAGE_ERROR
                )
                return HttpResponseRedirect(reverse("signup"))

            return HttpResponseRedirect(
                reverse('signup_activation',
                    kwargs={
                        'phone': form.cleaned_data['username']
                    }
                )
            )

        return render(request, self.template_name, {'form': form})


class ActivationView(View):

    """
    User account activation
    """

    form_class = ActivationForm
    initial = {}
    template_name = 'sms_signup/activation.html'

    def get(self, request, *args, **kwargs):
        phone = kwargs.get('phone', None)
        # Init form with the phone number
        self.initial['username'] = phone
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['username']

            # Compares the db sms code and request sms code
            sms_code_value = form.cleaned_data['sms_code']
            try:
                worker_sms_code = ActivationSMSCode.objects.get(
                    sms_code=sms_code_value,
                    phone=phone
                )
            except ActivationSMSCode.DoesNotExist:
                messages.add_message(
                    request,
                    messages.ERROR,
                    WRONG_ACTIVATION_CODE
                )
                return HttpResponseRedirect(reverse("signup_activation"))

            if not worker_sms_code.is_activated:
                # Checks that activation period is not expired
                signup_time = datetime.datetime.utcnow().replace(
                    tzinfo=utc) - timedelta(days=ACTIVATION_PERIOD)
                if signup_time < worker_sms_code.sms_code_init_time:
                    # Creates the user
                    password = User.objects.make_random_password()
                    username = form.cleaned_data['username']
                    user = self.create_user(
                        phone=username,
                        password=password
                    )
                    worker_sms_code.is_activated = True
                    worker_sms_code.save()
                    # Sends the password in the sms
                    api.send_sms(
                        body=" ".join(["Password:", password]),
                        from_phone=settings.PHONE_NUMBER_FROM,
                        to=[phone],
                        flash=True
                    )

                    messages.add_message(
                        request,
                        messages.INFO,
                        ACCOUNT_ACTIVATED
                    )

                    # Authenticates the user
                    return login(request, username, password)
                else:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        ACTIVATION_PERIOD_EXPIRED
                    )
                    HttpResponseRedirect(reverse("signup"))
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    ACTIVATION_ALREADY_HAS_BEEN
                )
                return HttpResponseRedirect(reverse("signup"))

        return render(request, self.template_name, {'form': form})

    def create_user(self, phone, password):
        """
        Creating the user
        """

        user = User.objects.create_user(
            username=phone,
            password=password,
            email=phone
        )
        user.backend = SMSAuthBackend
        user.save()
        return user


class LoginView(View):

    """
    User login
    """

    form_class = LoginForm
    initial = {}
    template_name = 'sms_signup/login.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            return login(
                request,
                request.POST['username'],
                request.POST['password']
            )

        return render(request, self.template_name, {'form': form})

    def logout(request):
        auth.logout(request)
        return HttpResponseRedirect("/account/loggedout/")


def login(request, username, password):
    """
    Log in the user
    """

    user = auth.authenticate(
        username=username,
        password=password
    )

    if user is not None and user.is_active:
        auth.login(request, user)
        return HttpResponseRedirect(reverse("home"))
    else:
        messages.add_message(
            request,
            messages.ERROR,
            LOGIN_ERROR
        )
        return HttpResponseRedirect(reverse("login"))
