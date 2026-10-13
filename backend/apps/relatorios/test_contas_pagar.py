from datetime import date
from django.test import TestCase
from apps.financeiro.models import CategoriaFinanceira, LancamentoFinanceiro
from .selectors import selecionar_relatorio_operacional
from .serializers import FiltrosRelatorioOperacionalSerializer

class ContasPagarTests(TestCase):
    def test_exclui_receber_preserva_status_e_filtra_vencimento(self):
        categoria = CategoriaFinanceira.objects.create(nome="Contas")
        for tipo, status, dia in [("pagar", "pendente", 7), ("pagar", "liquidado", 8), ("pagar", "cancelado", 9), ("receber", "pendente", 7), ("pagar", "pendente", 20)]:
            LancamentoFinanceiro.objects.create(tipo=tipo,status=status,descricao=tipo,valor="100",categoria=categoria,data_vencimento=date(2026,10,dia))
        filtros=FiltrosRelatorioOperacionalSerializer(data={"secao":"contas_pagar","data_inicio":"2026-10-07","data_fim":"2026-10-09","por_pagina":2})
        filtros.is_valid(raise_exception=True)
        dados=selecionar_relatorio_operacional(**filtros.validated_data)
        self.assertEqual(dados["dados"]["total"],3)
        self.assertEqual(len(dados["dados"]["resultados"]),2)
        self.assertTrue(all(i["tipo"]=="Conta a pagar" for i in dados["dados"]["resultados"]))
        segunda=selecionar_relatorio_operacional(**{**filtros.validated_data,"pagina":2})
        self.assertEqual(len(segunda["dados"]["resultados"]),1)
        self.assertEqual(LancamentoFinanceiro.objects.count(),5)

    def test_agrupamento_preserva_identidade_e_exporta_toda_consulta(self):
        from .agrupamento_financeiro import agrupar_financeiro
        for i in range(30):
            LancamentoFinanceiro.objects.create(tipo="pagar",descricao="Sem cadastro",recebedor_nome="Mesmo nome",valor="10",data_vencimento=date(2026,10,7))
        qs=LancamentoFinanceiro.objects.all()
        grupos=agrupar_financeiro(qs,"fornecedor")
        self.assertEqual(grupos["total"],30)
        self.assertEqual(len(grupos["resultados"]),25)
        self.assertEqual(len(agrupar_financeiro(qs,"fornecedor",por_pagina=100000)["resultados"]),30)
        dia=agrupar_financeiro(qs,"dia")
        self.assertEqual(dia["total"],1)
        from decimal import Decimal
        self.assertEqual(Decimal(dia["resultados"][0]["pendente"]),Decimal("300"))

    def test_faixas_vencimento_limites_sem_cancelados_receber(self):
        from .agrupamento_financeiro import vencimentos_financeiros
        from unittest.mock import patch
        from datetime import timedelta
        hoje=date(2026,10,7)
        for dias in [-1,0,1,7,8,30,31]:
            LancamentoFinanceiro.objects.create(tipo="pagar",descricao="Faixa",valor="10",data_vencimento=hoje-timedelta(days=dias))
        for tipo,status in [("receber","pendente"),("pagar","cancelado"),("pagar","liquidado")]:
            LancamentoFinanceiro.objects.create(tipo=tipo,status=status,descricao="Não pendente pagar",valor="999",data_vencimento=hoje-timedelta(days=50))
        with patch("django.utils.timezone.localdate",return_value=hoje):
            r=vencimentos_financeiros(LancamentoFinanceiro.objects.all())
        self.assertEqual([f["quantidade"] for f in r["faixas"]],[1,1,2,2,1])
        from decimal import Decimal
        self.assertEqual(sum(Decimal(f["valor"]) for f in r["faixas"]),Decimal("70"))
