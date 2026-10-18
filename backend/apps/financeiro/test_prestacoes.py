from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase
from .prestacoes import Parametros, calcular


class PrestacoesTests(SimpleTestCase):
    def parametros(self, **kwargs):
        p=Parametros(data=dict(valor='565000', entrada='113000', juros_anual='10', parcelas=5, liberacao='2026-10-16', primeiro_vencimento='2027-10-16', periodicidade='anual', **kwargs))
        self.assertTrue(p.is_valid(),p.errors)
        return p.validated_data

    def test_referencia_planilha_e_ano_bissexto(self):
        r=calcular(self.parametros())
        self.assertEqual(r['financiado'],'452000.00')
        self.assertEqual(r['parcelas'][0]['prestacao'],'135600.00')
        self.assertEqual(r['parcelas'][1]['dias'],366)
        self.assertEqual(r['parcelas'][-1]['prestacao'],'99440.00')
        self.assertLessEqual(abs(Decimal(r['total_prestacoes'])-Decimal('587703.8781567848')),Decimal('.02'))
        self.assertEqual(r['parcelas'][-1]['saldo'],'0.00')
        self.assertEqual(sum(Decimal(i['prestacao']) for i in r['parcelas']),Decimal(r['total_prestacoes']))

    def test_sem_juros_arredondamento_e_fim_do_mes(self):
        dados=self.parametros();dados.update(valor=Decimal('100'),entrada=Decimal(0),juros_anual=Decimal(0),parcelas=3,liberacao=date(2026,1,1),primeiro_vencimento=date(2026,1,31),periodicidade='mensal')
        r=calcular(dados)
        self.assertEqual(r['juros'],'0.00'); self.assertEqual(r['total_prestacoes'],'100.00')
        self.assertEqual(r['parcelas'][1]['vencimento'],'2026-02-28')
        self.assertEqual(r['parcelas'][2]['vencimento'],'2026-03-31')

    def test_parametros_invalidos(self):
        base=self.parametros()
        for campo,valor in [('entrada','565000'),('juros_anual','-1'),('juros_anual','NaN'),('parcelas',0),('parcelas',361),('primeiro_vencimento','2026-01-01')]:
            p=Parametros(data={**base,campo:valor})
            self.assertFalse(p.is_valid(),campo)

    def test_principal_de_centavos_nunca_negativo(self):
        dados=self.parametros();dados.update(valor=Decimal('.02'),entrada=Decimal(0),juros_anual=Decimal(0),parcelas=4)
        resultado=calcular(dados)
        self.assertEqual(resultado['total_prestacoes'],'0.02')
        self.assertTrue(all(Decimal(p['saldo'])>=0 and Decimal(p['amortizacao'])>=0 for p in resultado['parcelas']))

    def test_carencia_explicita_paga_juros_sem_amortizar(self):
        dados=self.parametros();dados['carencia']=1
        resultado=calcular(dados)
        self.assertEqual(len(resultado['parcelas']),6)
        self.assertEqual(resultado['parcelas'][0]['amortizacao'],'0.00')
        self.assertEqual(resultado['parcelas'][0]['saldo'],'452000.00')
        self.assertEqual(resultado['parcelas'][-1]['saldo'],'0.00')
