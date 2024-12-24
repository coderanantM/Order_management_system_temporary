from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_seller, name='register_seller'),
    path('login/', views.login_view, name='login_view'),
    path('', views.seller_dashboard, name='dashboard'),
    path('list-new-part/', views.list_new_part, name='list_new_part'),
    path('update-production/', views.update_daily_production, name='update_daily_production'),
    path('get-part-details/<str:part_code>/', views.get_part_details, name='get_part_details'),
    path('export_schedule/<str:part_code>/<str:date>/', views.export_schedule_for_date_to_csv, name='export_schedule_for_date_to_csv'),
    path('export_schedule/<str:part_code>/', views.export_schedule_to_csv, name='export_schedule_to_csv'),
]
