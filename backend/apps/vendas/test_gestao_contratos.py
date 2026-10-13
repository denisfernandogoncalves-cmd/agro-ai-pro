from decimal import Decimal
from rest_framework.test import APITestCase
from apps.graos.models import MovimentacaoGraos
from apps.core.models import RegistroAlteracao
from .tests import ContextoVendaMixin
from .models import ContratoComercial
from .services import confirmar_venda, registrar_entrega_venda, VendaGraosConflitoError

class GestaoContratoTests(ContextoVendaMixin, APITestCase):
    def setUp(self):
        self.criar_contexto()
        self.usuario.is_staff=True
        self.usuario.save()
        self.client.force_authenticate(self.usuario)
        self.contrato=ContratoComercial.objects.create(numero="GESTAO",empresa="Comprador",produto="Soja",quantidade_kg="1000")
        self.url=f"/api/comercial/contratos/{self.contrato.pk}/"
    def configurar(self,**dados):
        self.contrato.refresh_from_db()
        return self.client.patch(self.url,{"versao":self.contrato.versao,"justificativa":"Planejamento conferido",**dados},format="json")
    def cota(self,quantidade="500"):
        return [{"cad_pro":str(self.cadpro.pk),"quantidade_kg":quantidade}]
    def venda(self):
        v=self.rascunho();v.contrato=self.contrato;v.save(update_fields=["contrato"])
        confirmar_venda(usuario=self.usuario,venda=v,chave_idempotencia="confirmar-gestao")
        return v
    def test_configuracao_sem_movimento_historico_e_versao(self):
        before=MovimentacaoGraos.objects.count()
        r=self.configurar(cotas_cadpro=self.cota(),alerta_restante_kg="150")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data["versao"],2)
        self.assertEqual(MovimentacaoGraos.objects.count(),before)
        self.assertTrue(RegistroAlteracao.objects.filter(entidade="ContratoComercial",registro_id=str(self.contrato.pk)).exists())
        self.assertEqual(self.client.patch(self.url,{"versao":1,"justificativa":"Stale"},format="json").status_code,409)
    def test_limites_e_duplicidade(self):
        for c in (self.cota("1001"),self.cota()*2,self.cota("NaN"),self.cota("0")):
            r=self.configurar(cotas_cadpro=c);self.assertEqual(r.status_code,400,r.data)
    def test_entrega_reenvio_excesso_e_reducao(self):
        self.assertEqual(self.configurar(cotas_cadpro=self.cota("200")).status_code,200)
        v=self.venda()
        for _ in range(2):
            registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="150",chave_idempotencia="entrega-gestao")
        with self.assertRaises(VendaGraosConflitoError):
            registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="100",chave_idempotencia="excesso-gestao")
        v.refresh_from_db();self.assertEqual(v.quantidade_entregue_kg,Decimal("150"))
        self.assertEqual(self.configurar(cotas_cadpro=self.cota("100")).status_code,400)
        self.assertEqual(self.configurar(cotas_cadpro=[]).status_code,400)
    def test_alerta_e_saldo_compartilhado(self):
        self.configurar(cotas_cadpro=self.cota(),alerta_restante_kg="850")
        v=self.venda();registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="150",chave_idempotencia="alerta-gestao")
        r=self.client.get(self.url+"acompanhamento/");self.assertEqual(r.status_code,200,r.data)
        self.assertTrue(r.data["alerta"])
        self.assertEqual(Decimal(r.data["restante_kg"]),Decimal("850"))
        self.assertEqual(Decimal(r.data["cotas"][0]["disponivel_kg"]),Decimal("400"))
    def test_agenda_sem_movimento_e_cad_exato(self):
        before=MovimentacaoGraos.objects.count()
        r=self.configurar(calendario_entregas=[{**self.cota()[0],"data":"2026-10-08"}])
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(MovimentacaoGraos.objects.count(),before)
        self.assertEqual(self.configurar(cotas_cadpro=[{"cad_pro":"inexistente","quantidade_kg":"10"}]).status_code,400)
    def test_justificativa_e_autenticacao(self):
        self.assertEqual(self.client.patch(self.url,{"versao":1},format="json").status_code,400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url+"acompanhamento/").status_code,401)

    def test_cancelar_restante_preserva_entregas_validas_do_contrato(self):
        from .services import cancelar_venda
        self.configurar(cotas_cadpro=self.cota("200"))
        v=self.venda()
        registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="150",chave_idempotencia="parcial-cancelar")
        cancelar_venda(usuario=self.usuario,venda=v,chave_idempotencia="restante-cancelar")
        r=self.client.get(self.url+"acompanhamento/")
        self.assertEqual(Decimal(r.data["entregue_kg"]),Decimal("150"))
        self.assertEqual(self.configurar(cotas_cadpro=self.cota("100")).status_code,400)
    def test_edicao_de_entrega_nao_contorna_cota(self):
        from .alteracoes_services import alterar_movimento
        self.configurar(cotas_cadpro=self.cota("200"))
        v=self.venda()
        item=registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="150",chave_idempotencia="editar-cota")
        v.refresh_from_db()
        with self.assertRaises(VendaGraosConflitoError):
            alterar_movimento(usuario=self.usuario,venda=v,movimento_id=item.pk,natureza="entrega",excluir=False,versao=v.versao,motivo="Conferência",quantidade_kg="250",chave_idempotencia="edicao-excede")

    def test_inativacao_requer_versao(self):
        self.assertEqual(self.client.delete(self.url,{},format="json").status_code,409)
        self.assertEqual(self.client.delete(self.url,{"versao":1,"justificativa":"Encerrado"},format="json").status_code,204)
        self.assertEqual(self.client.delete(self.url,{"versao":1,"justificativa":"Antigo"},format="json").status_code,409)

    def test_cota_antiga_preserva_cad_inativo_sem_novo_vinculo(self):
        self.assertEqual(self.configurar(cotas_cadpro=self.cota()).status_code,200)
        self.cadpro.ativo=False
        self.cadpro.save(update_fields=["ativo"])
        r=self.configurar(alerta_restante_kg="100")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(r.data["cotas_cadpro"][0]["cad_pro"],str(self.cadpro.pk))
        self.assertEqual(self.configurar(cotas_cadpro=[]).status_code,200)
        self.assertEqual(self.configurar(cotas_cadpro=self.cota()).status_code,400)

    def test_cobertura_reserva_propria_sem_duplicar_disponivel(self):
        self.assertEqual(self.configurar(cotas_cadpro=self.cota("1000")).status_code,200)
        v=self.venda()
        r=self.client.get(self.url+"acompanhamento/")
        c=r.data["cotas"][0]
        v.refresh_from_db()
        self.assertEqual(Decimal(c["reservado_proprio_contrato_kg"]),v.quantidade_reservada_kg)
        self.assertEqual(Decimal(c["cobertura_kg"]),Decimal(c["disponivel_kg"])+v.quantidade_reservada_kg)
        registrar_entrega_venda(usuario=self.usuario,venda=v,quantidade_kg="150",chave_idempotencia="cobertura-parcial")
        c=self.client.get(self.url+"acompanhamento/").data["cotas"][0]
        v.refresh_from_db()
        self.assertEqual(Decimal(c["reservado_proprio_contrato_kg"]),v.quantidade_reservada_kg)
        self.assertEqual(Decimal(c["restante_kg"]),Decimal("850"))

    def test_cobertura_exclui_reserva_de_outro_contrato_e_recalcula_cancelamento(self):
        from .services import cancelar_venda
        self.configurar(cotas_cadpro=self.cota("1000"))
        propria=self.venda()
        outra=self.rascunho(numero="OUTRO",quantidade="200")
        confirmar_venda(usuario=self.usuario,venda=outra,chave_idempotencia="reserva-outro")
        c=self.client.get(self.url+"acompanhamento/").data["cotas"][0]
        self.assertEqual(Decimal(c["comprometido_outros_kg"]),Decimal("200"))
        self.assertEqual(Decimal(c["cobertura_kg"]),Decimal("800"))
        self.assertEqual(Decimal(c["falta_com_reserva_propria_kg"]),Decimal("200"))
        cancelar_venda(usuario=self.usuario,venda=propria,chave_idempotencia="cancela-reserva-propria")
        c=self.client.get(self.url+"acompanhamento/").data["cotas"][0]
        self.assertEqual(Decimal(c["reservado_proprio_contrato_kg"]),Decimal("0"))
        self.assertEqual(Decimal(c["cobertura_kg"]),Decimal("800"))

    def test_cobertura_oculta_saldos_sem_permissao_de_producao(self):
        from apps.accounts.models import AcessoUsuario
        self.configurar(cotas_cadpro=self.cota())
        self.usuario.is_staff=False
        self.usuario.save(update_fields=["is_staff"])
        AcessoUsuario.objects.update_or_create(usuario=self.usuario,defaults={"modulos":["vendas"],"permissoes":{"vendas":["consultar"]}})
        r=self.client.get(self.url+"acompanhamento/")
        self.assertEqual(r.status_code,200,r.data)
        c=r.data["cotas"][0]
        for campo in ("fisico_kg","comprometido_kg","disponivel_kg","reservado_proprio_contrato_kg","comprometido_outros_kg","cobertura_kg","falta_com_reserva_propria_kg"):
            self.assertIsNone(c[campo],campo)
        self.assertEqual(Decimal(c["quantidade_kg"]),Decimal("500"))
