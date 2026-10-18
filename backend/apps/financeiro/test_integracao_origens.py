from datetime import date
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from apps.transportes.models import Caminhao, LancamentoTransporte, RemuneracaoMotorista
from apps.maquinas.models import Maquina, ManutencaoMaquina
from .models import LancamentoFinanceiro
from .services import liquidar_lancamento
from .integracao import sincronizar
from .serializers import LancamentoFinanceiroSerializer


class IntegracaoOrigensTests(TestCase):
    def setUp(self):
        self.caminhao = Caminhao.objects.create(placa="ABC1D23", veiculo="Caminhão")

    def lancar(self, **dados):
        campos = dict(caminhao=self.caminhao, motorista="João", data=date(2026, 10, 15),
                      tipo="despesa", descricao="Pedágio", quantidade=Decimal("1"), valor_unitario=Decimal("50"))
        campos.update(dados)
        return LancamentoTransporte.objects.create(**campos)

    def test_despesa_nova_titulo_unico_e_edicao(self):
        origem = self.lancar()
        self.assertEqual(origem.conta_pagar.valor, Decimal("50"))
        self.assertEqual(origem.conta_pagar.status, "pendente")
        origem.valor_unitario = Decimal("75")
        origem.save()
        sincronizar(origem)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 1)
        origem.refresh_from_db()
        self.assertEqual(origem.conta_pagar.valor, Decimal("75"))

    def test_receita_silo_e_zero_nao_duplicam_obrigacao(self):
        self.lancar(tipo="receita")
        self.lancar(abasteceu_silo=True)
        self.lancar(valor_unitario=Decimal("0"))
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_historicos_e_importacoes_nao_geram_contas(self):
        antigo = self.lancar(integrar_financeiro=False)
        antigo.valor_unitario = Decimal("100")
        antigo.save()
        self.lancar(chave_importacao="historico")
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_remuneracao_comissao_acompanha_lancamentos(self):
        rem = RemuneracaoMotorista.objects.create(caminhao=self.caminhao, motorista="João",
            competencia=date(2026, 10, 1), salario=Decimal("2000"), comissao_percentual=Decimal("10"))
        receita = self.lancar(tipo="receita", valor_unitario=Decimal("1000"))
        rem.refresh_from_db()
        self.assertEqual(rem.conta_pagar.valor, Decimal("2100"))
        receita.delete()
        rem.refresh_from_db()
        self.assertEqual(rem.conta_pagar.valor, Decimal("2000"))

    def test_liquidacao_bloqueia_edicao_e_exclusao_sem_gravacao_parcial(self):
        origem = self.lancar()
        liquidar_lancamento(origem.conta_pagar, data_liquidacao=date(2026, 10, 15), valor_liquidado=Decimal("50"))
        origem.valor_unitario = Decimal("100")
        with self.assertRaises(ValidationError):
            origem.save()
        origem.refresh_from_db()
        self.assertEqual(origem.valor_unitario, Decimal("50"))
        with self.assertRaises(ValidationError):
            origem.delete()
        self.assertTrue(LancamentoTransporte.objects.filter(pk=origem.pk).exists())

    def test_exclusao_cancela_titulo_e_preserva_historico_financeiro(self):
        origem = self.lancar()
        conta_id = origem.conta_pagar_id
        LancamentoTransporte.objects.filter(pk=origem.pk).delete()
        self.assertEqual(LancamentoFinanceiro.objects.get(pk=conta_id).status, "cancelado")

    def test_manutencao_somente_concluida_com_custo(self):
        maquina = Maquina.objects.create(identificacao="Trator", tipo="trator")
        manutencao = ManutencaoMaquina.objects.create(maquina=maquina, descricao="Oficina", data_prevista=date(2026, 10, 15))
        self.assertIsNone(manutencao.conta_pagar_id)
        manutencao.status = "concluida"
        manutencao.data_conclusao = date(2026, 10, 15)
        manutencao.custo = Decimal("300")
        manutencao.save()
        self.assertEqual(manutencao.conta_pagar.valor, Decimal("300"))
        manutencao.status = "cancelada"
        manutencao.save()
        manutencao.refresh_from_db()
        self.assertEqual(manutencao.conta_pagar.status, "cancelado")

    def test_valor_protegido_e_vencimento_conferivel_no_financeiro(self):
        origem = self.lancar()
        serializer = LancamentoFinanceiroSerializer(origem.conta_pagar, data={"valor": "999"}, partial=True)
        self.assertFalse(serializer.is_valid())
        serializer = LancamentoFinanceiroSerializer(origem.conta_pagar, data={"data_vencimento": "2026-11-20"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        origem.valor_unitario = Decimal("60")
        origem.save()
        origem.refresh_from_db()
        self.assertEqual(origem.conta_pagar.data_vencimento, date(2026, 11, 20))

    def test_cancelamento_financeiro_exige_ajustar_origem(self):
        origem = self.lancar()
        cliente = APIClient()
        cliente.force_authenticate(get_user_model().objects.create_superuser("admin-integracao", password="senha-teste"))
        resposta = cliente.post(f"/api/financeiro/lancamentos/{origem.conta_pagar_id}/cancelar/")
        self.assertEqual(resposta.status_code, 409)
        origem.conta_pagar.refresh_from_db()
        self.assertEqual(origem.conta_pagar.status, "pendente")

    def test_compra_antiga_sem_vinculo_aguarda_conferencia(self):
        from apps.estoque.models import ProdutoEstoque, LoteEstoque, MovimentacaoEstoque, CompraEstoque
        from apps.estoque.compra_financeiro import sincronizar_compra_financeiro
        from .models import ParceiroFinanceiro
        fornecedor = ParceiroFinanceiro.objects.create(nome="Fornecedor", tipo="fornecedor")
        produto = ProdutoEstoque.objects.create(nome="Insumo", categoria="insumo", unidade="l")
        lote = LoteEstoque.objects.create(produto=produto, fornecedor=fornecedor, codigo="antigo")
        movimento = MovimentacaoEstoque.objects.create(lote=lote, tipo="entrada", quantidade=10,
            custo_unitario=5, criado_por=get_user_model().objects.create_user("comprador"))
        compra = CompraEstoque.objects.create(id=uuid.uuid4(), assinatura="historico", movimento=movimento,
            integrar_financeiro=False, quantidade_embalagens=1, embalagem="GL", conteudo_embalagem=10,
            custo_embalagem=50, valor_total=50)
        self.assertIsNone(sincronizar_compra_financeiro(compra))
        compra.refresh_from_db()
        self.assertIsNone(compra.conta_pagar_id)
        self.assertFalse(LancamentoFinanceiro.objects.exists())
