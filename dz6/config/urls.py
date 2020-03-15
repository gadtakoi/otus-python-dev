from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from qna.views import IndexView, TagSearchView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', admin.site.urls),
    path('hot/', IndexView.as_view(), {'variant': 'hot'}, name='hot'),
    path('tag/<str:tag>/', TagSearchView.as_view(), name='tag'),
    path('', include('qna.urls')),
    path('', include('customuser.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
