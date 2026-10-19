from types import SimpleNamespace

from django.test import SimpleTestCase

from .serializers import PropriedadeSerializer


class ApelidosTests(SimpleTestCase):
    def test_preserva_variantes_sem_repetir_e_ignora_outras_origens(self):
        def linha(valor, tipo="historico", planilha="INSUMOS"):
            return SimpleNamespace(tipo=tipo, planilha=planilha, linha_origem=8,
                dados_normalizados={"valores_por_celula": {"D8": valor}})

        linhas = [linha(" SILO "), linha("silo"), linha("SCARAMAL"),
                  linha(0), linha(""), linha("Outro", tipo="producao"),
                  linha("Outro", planilha="1")]
        propriedade = SimpleNamespace(apelido='', linhas_importacao=SimpleNamespace(all=lambda: linhas))
        self.assertEqual(PropriedadeSerializer().get_apelidos(propriedade), ["SCARAMAL", "SILO"])

    def test_sem_importacao_retorna_lista_vazia(self):
        propriedade = SimpleNamespace(apelido='', linhas_importacao=SimpleNamespace(all=lambda: []))
        self.assertEqual(PropriedadeSerializer().get_apelidos(propriedade), [])
