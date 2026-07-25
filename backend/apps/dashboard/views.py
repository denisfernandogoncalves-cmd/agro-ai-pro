from django.shortcuts import render


def dashboard_home(request):
    contexto = {
        "titulo": "AGRO-AI-PRO Dashboard",
        "mensagem": "Sistema Agro Inteligente iniciado com sucesso"
    }

    return render(request, "dashboard/home.html", contexto)