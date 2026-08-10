from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.propriedades.models import Propriedade

from ..models import CADPro, CADProPropriedade, normalizar_codigo_cadpro


def criar_propriedade(nome="Fazenda Modelo"):
    return Propriedade.objects.create(
        nome=nome,
        municipio="Cascavel",
        uf="PR",
        area_hectares="100.00",
    )


class CADProModelTests(TestCase):
    def test_normalizacao_deterministica_e_unicidade(self):
        self.assertEqual(normalizar_codigo_cadpro(" áb-12. 03 "), "AB1203")
        cad_pro = CADPro.objects.create(
            codigo=" áb-12. 03 ",
            descricao="  Produtor   principal ",
        )
        self.assertEqual(cad_pro.codigo, "áb-12. 03")
        self.assertEqual(cad_pro.codigo_normalizado, "AB1203")
        self.assertEqual(cad_pro.descricao, "Produtor principal")
        with self.assertRaises(ValidationError):
            CADPro.objects.create(codigo="AB 1203", descricao="Duplicado")

    def test_codigo_sem_letras_ou_numeros_e_rejeitado(self):
        with self.assertRaises(ValidationError):
            CADPro.objects.create(codigo=" / - ", descricao="Inválido")

    def test_vinculos_sao_unicos_e_protegidos(self):
        cad_pro = CADPro.objects.create(codigo="1234567", descricao="Titular")
        propriedade = criar_propriedade()
        vinculo = CADProPropriedade.objects.create(
            cad_pro=cad_pro,
            propriedade=propriedade,
        )
        with self.assertRaises(ValidationError):
            CADProPropriedade.objects.create(
                cad_pro=cad_pro,
                propriedade=propriedade,
            )
        with self.assertRaises(ProtectedError):
            cad_pro.delete()
        with self.assertRaises(ProtectedError):
            propriedade.delete()
        self.assertTrue(CADProPropriedade.objects.filter(pk=vinculo.pk).exists())

    def test_cadpro_inativo_bloqueia_novo_vinculo(self):
        cad_pro = CADPro.objects.create(
            codigo="7654321",
            descricao="Inativo",
            ativo=False,
        )
        with self.assertRaises(ValidationError):
            CADProPropriedade.objects.create(
                cad_pro=cad_pro,
                propriedade=criar_propriedade(),
            )
        with self.assertRaises(ValidationError):
            CADProPropriedade.objects.create(
                cad_pro=cad_pro,
                propriedade=criar_propriedade("Vínculo inativo"),
                ativo=False,
            )

    def test_cadpro_inativo_preserva_vinculo_historico_sem_permitir_reativacao(self):
        cad_pro = CADPro.objects.create(codigo="9999999", descricao="Histórico")
        vinculo = CADProPropriedade.objects.create(
            cad_pro=cad_pro,
            propriedade=criar_propriedade(),
        )
        cad_pro.ativo = False
        cad_pro.save()
        vinculo.save()
        vinculo.ativo = False
        vinculo.save()
        vinculo.ativo = True
        with self.assertRaises(ValidationError):
            vinculo.save()
