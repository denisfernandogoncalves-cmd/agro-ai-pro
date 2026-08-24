from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers

from apps.cadpro.models import CADPro, CADProPropriedade
from apps.propriedades.models import Propriedade

from .models import ArmazemGraos, LoteGraos
from .serializers import ArmazemGraosSerializer
from .services import creditar_producao


class ArmazemGraosSerializerTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="armazem_serializer",
            password="senha-segura-teste",
        )
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda do Armazém",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        self.cad_pro = CADPro.objects.create(
            codigo="CAD-ARMAZEM-SERIALIZER",
            descricao="Teste de armazenagem",
        )
        CADProPropriedade.objects.create(
            cad_pro=self.cad_pro,
            propriedade=self.propriedade,
        )
        self.armazem = ArmazemGraos.objects.create(
            propriedade=self.propriedade,
            nome="Silo principal",
            capacidade_kg="1000.000",
        )
        self.lote = LoteGraos.objects.create(
            armazem=self.armazem,
            cad_pro=self.cad_pro,
            codigo="LOTE-ARMAZEM-SERIALIZER",
            cultura="Soja",
            safra="2026/2027",
            classificacao_codigo="PADRAO",
        )

    def test_revalida_ocupacao_ao_salvar_e_rejeita_validacao_obsoleta(self):
        serializer = ArmazemGraosSerializer(
            self.armazem,
            data={"capacidade_kg": "600.000"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        creditar_producao(
            usuario=self.usuario,
            lote=self.lote,
            quantidade_kg="700.000",
            chave_idempotencia="teste:armazem:ocupacao-concorrente",
        )

        with self.assertRaises(serializers.ValidationError):
            serializer.save()
        self.armazem.refresh_from_db()
        self.assertEqual(str(self.armazem.capacidade_kg), "1000.000")

    def test_propriedade_e_imutavel_apos_cadastro(self):
        outra = Propriedade.objects.create(
            nome="Outra Fazenda",
            municipio="Sorriso",
            uf="MT",
            area_hectares="100",
        )
        serializer = ArmazemGraosSerializer(
            self.armazem,
            data={"propriedade": outra.pk},
            partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("propriedade", serializer.errors)
