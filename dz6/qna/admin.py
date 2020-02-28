from django.contrib import admin

from qna.models import Question, Answer, Tag, User

admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Tag)
admin.site.register(User)
