import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework.response import Response
from rest_framework.views import APIView


@require_GET
@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({"status": "ok"})


@require_POST
@csrf_protect
def login_view(request):
    try:
        credentials = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"detail": "Solicitud inválida"}, status=400)
    if not isinstance(credentials, dict):
        return JsonResponse({"detail": "Solicitud inválida"}, status=400)
    username = credentials.get("username")
    password = credentials.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"detail": "Solicitud inválida"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Credenciales inválidas"}, status=401)
    login(request, user)
    return JsonResponse({"id": user.pk, "username": user.get_username(), "is_admin": user.is_staff})


@require_POST
@csrf_protect
def logout_view(request):
    logout(request)
    return JsonResponse({"status": "ok"})


class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response({
            "id": user.pk,
            "username": user.get_username(),
            "first_name": user.first_name,
            "is_admin": user.is_staff,
        })
