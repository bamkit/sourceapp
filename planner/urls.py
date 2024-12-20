from django.urls import path
from .views import HomeView, StatsView, UploadPolygonView, LoadPreplotView, LoadSequenceView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('stats/', StatsView.as_view(), name='stats'),
    path('upload_polygon/', UploadPolygonView.as_view(), name='upload_polygon'),
    path('load-preplot/', LoadPreplotView.as_view(), name='load_preplot'),
    path('load-sequence/', LoadSequenceView.as_view(), name='load_sequence'),
]