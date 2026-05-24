"""URL routing for the financing app.

"""

from django.urls import path

from .views import FinancingListView

urlpatterns = [
    path('', FinancingListView.as_view(), name='financing-list-create'),
]

