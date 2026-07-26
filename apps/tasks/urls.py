from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.TaskBoardView.as_view(), name="board"),
    path("nueva/", views.TaskCreateView.as_view(), name="create"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.TaskUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.TaskDeleteView.as_view(), name="delete"),
    path("<int:pk>/comentar/", views.TaskCommentView.as_view(), name="comment"),
]
