from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.core.mail import EmailMessage
from django.shortcuts import render

from qna.models import Question


def send_email_answer_alert(question_id: str, request: WSGIRequest) -> bool:
    out = False
    try:
        question = Question.objects.get(id=int(question_id))
    except Question.DoesNotExist:
        question = None

    if question:
        host = get_host(request)

        subject = 'New answer'
        message = '{} to question "{}" here {}/question/{}/'.format(subject, question, host, question.id)
        to_email = (question.author.email,)
        msg = EmailMessage(subject=subject,
                           body=message,
                           from_email=settings.EMAIL_FROM_ADDRESS,
                           to=to_email)
        msg.send()
        out = True

    return out


def get_host(request: WSGIRequest) -> str:
    protocol = 'http'
    if request.is_secure():
        protocol = 'https'
    host = "{}://{}".format(protocol, request.get_host())
    return host
