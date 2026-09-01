from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, BrokenBarrierError, local
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from . import cargas_services
from .models import ArmazemGraos, CargaColhida, MovimentacaoGraos, PosicaoSaldoGraos
from .test_cargas_colhidas import CargaColhidaBase


@skipUnless(connection.vendor == "postgresql", "Requer bloqueios reais do PostgreSQL.")
class RateioConcorrentePostgreSQLTests(CargaColhidaBase, TransactionTestCase):
    def setUp(self):
        self.criar_contexto()
        self.outra_propriedade = Propriedade.objects.create(
            nome="Fazenda Secundária", municipio="Sorriso", uf="MT", area_hectares="500",
        )
        self.outro_cadpro = CADPro.objects.create(codigo="CAD-SECUNDARIO", descricao="Outro titular")
        CADProPropriedade.objects.create(cad_pro=self.cad_pro, propriedade=self.outra_propriedade)
        for propriedade in (self.propriedade, self.outra_propriedade):
            CADProPropriedade.objects.create(cad_pro=self.outro_cadpro, propriedade=propriedade)
        self.outro_armazem = ArmazemGraos.objects.create(nome="Silo externo", capacidade_kg="100000")

    def dados(self, indice):
        dados = self.dados_carga()
        dados.pop("grupo_colheita")
        cadpros = (self.cad_pro, self.outro_cadpro) if indice == 0 else (self.outro_cadpro, self.cad_pro)
        dados.update(
            propriedade=self.propriedade, cad_pro=cadpros[0], cultura="Soja", safra="2026/2027",
            armazem=self.armazem if indice == 0 else self.outro_armazem,
            placa="AAA1A11" if indice == 0 else "BBB2B22",
            umidade_percentual="13.00", impureza_percentual="0.00", defeitos_percentual="0.00",
            propriedades_selecionadas=[self.propriedade.pk, self.outra_propriedade.pk],
            cadpros_por_propriedade={
                str(self.propriedade.pk): str(cadpros[0].pk),
                str(self.outra_propriedade.pk): str(cadpros[1].pk),
            },
        )
        return dados

    def executar_concorrencia(self, operacao):
        cargas = []
        if operacao != "registro":
            cargas = [cargas_services.registrar_carga_colhida(usuario=self.usuario, **self.dados(i)) for i in range(2)]
        inicio = Barrier(2)
        primeiras_parcelas = Barrier(2)
        estado_thread = local()
        nome_servico = "creditar_producao" if operacao == "registro" else "estornar_movimentacao"
        servico = getattr(cargas_services, nome_servico)

        def intercalar_parcelas(**kwargs):
            resultado = servico(**kwargs)
            if not getattr(estado_thread, "primeira_parcela", False):
                estado_thread.primeira_parcela = True
                # Força a disputa entre parcelas quando não há bloqueio global.
                # Com serialização correta, a primeira operação segue após o limite.
                try:
                    primeiras_parcelas.wait(timeout=1)
                except BrokenBarrierError:
                    pass
            return resultado

        def executar(indice):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SET statement_timeout = '15s'")
                inicio.wait(timeout=10)
                if operacao == "registro":
                    return cargas_services.registrar_carga_colhida(usuario=self.usuario, **self.dados(indice)).pk
                if operacao == "cancelamento":
                    return cargas_services.cancelar_carga_colhida(usuario=self.usuario, carga=cargas[indice]).pk
                dados = self.dados(indice)
                dados["peso_bruto_kg"] = "900.000"
                return cargas_services.corrigir_carga_colhida(usuario=self.usuario, carga=cargas[indice], **dados).pk
            finally:
                connection.close()

        with patch.object(cargas_services, nome_servico, side_effect=intercalar_parcelas):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futuros = [executor.submit(executar, indice) for indice in range(2)]
                resultados = [futuro.result(timeout=25) for futuro in futuros]
        self.assertEqual(len(set(resultados)), 2)
        esperado = {"registro": "2000", "cancelamento": "0", "correcao": "1800"}[operacao]
        self.assertEqual(sum(PosicaoSaldoGraos.objects.values_list("saldo_fisico_kg", flat=True)), Decimal(esperado))
        self.assertEqual(CargaColhida.objects.filter(status=CargaColhida.Status.ATIVA).count(), 0 if operacao == "cancelamento" else 2)
        self.assertEqual(MovimentacaoGraos.objects.count(), {"registro": 4, "cancelamento": 8, "correcao": 12}[operacao])
        for posicao in PosicaoSaldoGraos.objects.all():
            self.assertEqual(posicao.saldo_fisico_kg, sum(posicao.movimentacoes.values_list("delta_fisico_kg", flat=True)))

    def test_registros_rateados_com_cadpros_cruzados(self):
        self.executar_concorrencia("registro")

    def test_cancelamentos_rateados_com_cadpros_cruzados(self):
        self.executar_concorrencia("cancelamento")

    def test_correcoes_rateadas_com_cadpros_cruzados(self):
        self.executar_concorrencia("correcao")
