from qna.models import Question, Tag


def popular(request):
    return {'popular': Question.objects.all().order_by('-vote_count', '-date_create')[:20],
            'tags':  Tag.objects.all(),
            }
