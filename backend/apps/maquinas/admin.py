from django.contrib import admin

from .models import AbastecimentoMaquina, Maquina, ManutencaoMaquina, UsoMaquina


admin.site.register(Maquina)
admin.site.register(UsoMaquina)
admin.site.register(AbastecimentoMaquina)
admin.site.register(ManutencaoMaquina)
