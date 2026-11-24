from django.shortcuts import render


def sin_permiso(request, exception=None):
    return render(request, "publico/403.html", status=403)
