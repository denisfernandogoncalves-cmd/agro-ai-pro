from django.test import TestCase

from apps.propriedades.models import Propriedade

from ..models import CADPro, CADProPropriedade
from ..services import (
    VinculoCADProInvalido,
    listar_propriedades_vinculadas,
    obter_cadpro_ativo,
    validar_vinculo,
)


class CADProServiceTests(TestCase):
    def setUp(self):
        self.cad_pro = CADPro.objects.create(codigo="1234567", descricao="Titular")
        self.propriedade = Propriedade.objects.create(
            nome="Fazenda Serviço",
            municipio="Toledo",
            uf="PR",
            area_hectares="80.00",
        )
        self.vinculo = CADProPropriedade.objects.create(
            cad_pro=self.cad_pro,
            propriedade=self.propriedade,
        )

    def test_servicos_publicos_com_vinculo_ativo(self):
        self.assertEqual(obter_cadpro_ativo(self.cad_pro.pk), self.cad_pro)
        self.assertEqual(
            validar_vinculo(self.cad_pro.pk, self.propriedade.pk),
            self.vinculo,
        )
        self.assertEqual(
            list(listar_propriedades_vinculadas(self.cad_pro.pk)),
            [self.propriedade],
        )

    def test_vinculo_inativo_nao_autoriza_origem_produtiva(self):
        self.vinculo.ativo = False
        self.vinculo.save()
        with self.assertRaisesMessage(VinculoCADProInvalido, "vínculo ativo"):
            validar_vinculo(self.cad_pro.pk, self.propriedade.pk)
        self.assertFalse(listar_propriedades_vinculadas(self.cad_pro.pk).exists())

    def test_cadpro_inativo_nao_autoriza_origem_produtiva(self):
        self.cad_pro.ativo = False
        self.cad_pro.save()
        with self.assertRaises(CADPro.DoesNotExist):
            obter_cadpro_ativo(self.cad_pro.pk)
        with self.assertRaisesMessage(VinculoCADProInvalido, "ativo não encontrado"):
            validar_vinculo(self.cad_pro.pk, self.propriedade.pk)
        with self.assertRaises(CADPro.DoesNotExist):
            listar_propriedades_vinculadas(self.cad_pro.pk)

    def test_identificadores_invalidos_geram_erros_de_dominio(self):
        with self.assertRaises(CADPro.DoesNotExist):
            obter_cadpro_ativo("uuid-invalido")
        with self.assertRaises(VinculoCADProInvalido):
            validar_vinculo("uuid-invalido", self.propriedade.pk)
        with self.assertRaises(VinculoCADProInvalido):
            validar_vinculo(self.cad_pro.pk, "propriedade-invalida")
