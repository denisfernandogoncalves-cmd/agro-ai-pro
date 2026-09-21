from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade
from .models import LoteGraos, PosicaoSaldoGraos
from .services import creditar_producao, painel_saldos_cadpro, transferir_saldo_fisico
from .tests import GraosSaldoBase


class ConsolidadoPropriedadeTests(GraosSaldoBase, TestCase):
    def test_tres_propriedades_dois_cadpros_historico_e_filtro(self):
        self.criar_contexto()
        self.creditar('100')
        segundo_cad = CADPro.objects.create(codigo='SEGUNDO', descricao='Segundo titular')
        for indice, cad in enumerate((self.cad_pro, segundo_cad), start=2):
            propriedade = Propriedade.objects.create(nome=f'Fazenda {indice}', municipio='Teste', area_hectares='10')
            CADProPropriedade.objects.create(propriedade=propriedade, cad_pro=cad)
            lote = LoteGraos.objects.create(codigo=f'LOTE-{indice}', propriedade=propriedade,
                cad_pro=cad, armazem=self.armazem, cultura='Soja', safra=self.lote.safra,
                classificacao_codigo='PADRAO')
            creditar_producao(usuario=self.usuario, lote=lote, quantidade_kg='100', chave_idempotencia=f'credito-{indice}')
        painel = painel_saldos_cadpro()
        self.assertEqual(painel['resumo']['propriedades'], 3)
        self.assertEqual(painel['resumo']['cadpros'], 2)
        self.assertEqual(len(painel['consolidado_propriedade']), 3)
        self.assertEqual(sum(p['saldo_fisico_kg'] for p in painel['consolidado_propriedade']), Decimal('300'))
        filtrado = painel_saldos_cadpro(propriedade=self.propriedade.pk)
        self.assertEqual(len(filtrado['consolidado_propriedade']), 1)
        self.assertEqual(filtrado['consolidado_propriedade'][0]['propriedade'], self.propriedade.pk)
        PosicaoSaldoGraos.objects.create(cad_pro=self.cad_pro, armazem=self.armazem,
            cultura='Soja', safra='2020/2021', classificacao_codigo='PADRAO')
        painel = painel_saldos_cadpro()
        self.assertEqual(painel['resumo']['propriedades'], 3)
        self.assertEqual(len(painel['consolidado_propriedade']), 4)
        self.assertTrue(any(p['propriedade'] is None for p in painel['consolidado_propriedade']))


class TransferenciasOpostasTests(GraosSaldoBase, TransactionTestCase):
    def test_transferencias_opostas_conservam_saldos_sem_deadlock(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Locks concorrentes exigem PostgreSQL.')
        self.criar_contexto()
        self.creditar('1000')
        outra = Propriedade.objects.create(nome='Outra', municipio='Teste', area_hectares='10')
        cad = CADPro.objects.create(codigo='CAD-OUTRO', descricao='Outro titular')
        CADProPropriedade.objects.create(cad_pro=cad, propriedade=outra)
        destino = LoteGraos.objects.create(codigo='DESTINO', cad_pro=cad, propriedade=outra,
            armazem=self.armazem, cultura='Soja', safra=self.lote.safra, classificacao_codigo='PADRAO')
        creditar_producao(usuario=self.usuario, lote=destino, quantidade_kg='1000', chave_idempotencia='credito-destino')
        barreira = Barrier(2)

        def transferir(par):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                origem, alvo = par
                barreira.wait(timeout=10)
                return transferir_saldo_fisico(usuario=self.usuario, lote_origem=origem,
                    lote_destino=alvo, quantidade_kg='100', chave_idempotencia=f'transferir-{origem.pk}').codigo
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(transferir, ((self.lote, destino), (destino, self.lote))))
        self.assertEqual(resultados, ['saldo_transferido', 'saldo_transferido'])
        self.assertEqual(list(PosicaoSaldoGraos.objects.values_list('saldo_fisico_kg', flat=True)), [Decimal('1000'), Decimal('1000')])
