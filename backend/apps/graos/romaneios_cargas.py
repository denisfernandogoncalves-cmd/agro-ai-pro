"""Romaneios próprios/compartilhados reutilizam os exportadores de duas vias."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.accounts.access import pode
from apps.accounts.views import NoStoreResponseMixin
from apps.vendas.romaneios import _numero
from .models import CargaColhida
from .romaneios_terceiros import gerar_pdf, gerar_excel


def campos_carga(c):
    produtores = list(c.rateios.select_related("propriedade", "cad_pro").all())
    nomes = "; ".join(f"{r.propriedade.nome} / {r.cad_pro.codigo}" for r in produtores) if produtores else f"{c.propriedade.nome} / {c.cad_pro.codigo}"
    def kg(v):
        return "Não informado" if v is None else f"{_numero(v)} kg"
    qualidade = f"Umidade {_numero(c.umidade_percentual)}% · Impureza {_numero(c.impureza_percentual)}% · Avariados {_numero(c.defeitos_percentual)}%"
    if c.cultura.casefold() == "trigo":
        qualidade += f" · PH {_numero(c.ph)}"
    return [("Romaneio", f"#{c.pk}"), ("Registrado em", timezone.localtime(c.criado_em).strftime("%d/%m/%Y %H:%M")), ("Responsável", c.criado_por.username), ("Origem", "Produção própria"), ("Situação", c.get_status_display()), ("Data da entrada", c.data_colheita.strftime("%d/%m/%Y")), ("Propriedades / CAD/PRO", nomes), ("Cultura / safra", f"{c.cultura} / {c.safra}"), ("Armazenagem", c.armazem.nome), ("Peso total", kg(c.peso_total_kg)), ("Tara", kg(c.tara_kg)), ("Bruto do produto", kg(c.peso_bruto_kg)), ("Peso líquido", kg(c.peso_liquido_kg)), ("Sacas de 60 kg", _numero(c.sacas_60kg)), ("Desconto (%)", _numero(c.desconto_total_percentual)), ("Desconto (kg)", kg(c.desconto_total_kg)), ("Qualidade", qualidade), ("Motorista / placa", f"{c.motorista or '—'} / {c.placa or 'Sem placa'}"), ("Movimento", str(c.movimentacao_id)), ("Observações", c.observacoes or "—"), ("Motivo de cancelamento", c.motivo_cancelamento or "—")]


class RomaneioCargaView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    excel = False

    def get(self, request, pk):
        if not pode(request.user, "cargas", "imprimir"):
            raise PermissionDenied()
        carga = get_object_or_404(CargaColhida.objects.select_related("propriedade", "cad_pro", "armazem", "criado_por"), pk=pk)
        try:
            conteudo = (gerar_excel if self.excel else gerar_pdf)(carga, campos=campos_carga(carga), titulo=f"ROMANEIO DE ENTRADA #{pk}")
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        extensao = "xlsx" if self.excel else "pdf"
        resposta = HttpResponse(conteudo, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if self.excel else "application/pdf")
        resposta["Content-Disposition"] = f'attachment; filename="romaneio-carga-{pk}.{extensao}"'
        return resposta
