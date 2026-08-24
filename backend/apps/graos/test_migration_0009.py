from datetime import date

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class CargaColhidaMigration0009Tests(TransactionTestCase):
    migrate_from = ("graos", "0008_grupocolheita_armazem_padrao_opcional")
    migrate_to = ("graos", "0009_cargacolhida_contexto_direto_e_cancelamento")

    def test_preserva_historico_e_impede_rollback_com_carga_direta(self):
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([self.migrate_from])
            apps = executor.loader.project_state([self.migrate_from]).apps
            Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
            Propriedade = apps.get_model("propriedades", "Propriedade")
            CADPro = apps.get_model("cadpro", "CADPro")
            Armazem = apps.get_model("graos", "ArmazemGraos")
            Lote = apps.get_model("graos", "LoteGraos")
            Posicao = apps.get_model("graos", "PosicaoSaldoGraos")
            Origem = apps.get_model("graos", "OrigemSaldoGraos")
            Movimento = apps.get_model("graos", "MovimentacaoGraos")
            Grupo = apps.get_model("graos", "GrupoColheita")
            Carga = apps.get_model("graos", "CargaColhida")

            usuario = Usuario.objects.create(username="migration-carga-0009")
            propriedade_grupo = Propriedade.objects.create(
                nome="Fazenda Grupo Migration 0009",
                municipio="Sorriso",
                uf="MT",
                area_hectares="100",
            )
            propriedade_saldo = Propriedade.objects.create(
                nome="Fazenda Saldo Migration 0009",
                municipio="Lucas do Rio Verde",
                uf="MT",
                area_hectares="120",
            )
            cad_grupo = CADPro.objects.create(
                codigo="MIG-0009-GRUPO",
                codigo_normalizado="MIG0009GRUPO",
                descricao="CAD/PRO do grupo legado",
            )
            cad_saldo = CADPro.objects.create(
                codigo="MIG-0009-SALDO",
                codigo_normalizado="MIG0009SALDO",
                descricao="CAD/PRO contabilizado no lote",
            )
            armazem_grupo = Armazem.objects.create(
                propriedade=propriedade_grupo,
                nome="Silo Migration 0009",
                capacidade_kg="10000",
                ativo=True,
            )
            armazem_saldo = Armazem.objects.create(
                propriedade=propriedade_saldo,
                nome="Silo Divergente Migration 0009",
                capacidade_kg="10000",
                ativo=True,
            )

            def criar_lote(*, armazem, cad_pro, codigo, cultura, safra):
                return Lote.objects.create(
                    armazem=armazem,
                    cad_pro=cad_pro,
                    codigo=codigo,
                    cultura=cultura,
                    safra=safra,
                    classificacao_codigo="PADRAO",
                )

            lote_ativo = criar_lote(
                armazem=armazem_grupo,
                cad_pro=cad_grupo,
                codigo="MIG-0009-ATIVA",
                cultura="Soja",
                safra="2026/2027",
            )
            lote_cancelado = criar_lote(
                armazem=armazem_grupo,
                cad_pro=cad_grupo,
                codigo="MIG-0009-CANCELADA",
                cultura="Soja",
                safra="2026/2027",
            )
            lote_divergente = criar_lote(
                armazem=armazem_saldo,
                cad_pro=cad_saldo,
                codigo="MIG-0009-DIVERGENTE",
                cultura="Milho",
                safra="2027/2028",
            )

            def criar_grupo(nome):
                return Grupo.objects.create(
                    propriedade=propriedade_grupo,
                    cad_pro=cad_grupo,
                    criado_por=usuario,
                    nome=nome,
                    cultura="Soja",
                    safra="2026/2027",
                )

            grupo_ativo = criar_grupo("Grupo carga ativa")
            grupo_cancelado = criar_grupo("Grupo carga cancelada")
            grupo_divergente = criar_grupo("Grupo carga divergente")

            def criar_movimento_producao(*, lote, sufixo):
                posicao, _ = Posicao.objects.get_or_create(
                    cad_pro=lote.cad_pro,
                    cultura=lote.cultura,
                    safra=lote.safra,
                    classificacao_codigo=lote.classificacao_codigo,
                    armazem=lote.armazem,
                    defaults={
                        "saldo_fisico_kg": "100.000",
                        "saldo_comprometido_kg": "0.000",
                        "versao": 1,
                    },
                )
                origem = Origem.objects.create(
                    tipo="producao",
                    chave_idempotencia=f"migration-0009-origem-{sufixo}",
                    referencia_externa=f"migration-0009-{sufixo}",
                    hash_requisicao=sufixo * 64,
                    metadados={"migration": "0009"},
                    criado_por=usuario,
                )
                movimento = Movimento.objects.create(
                    tipo="entrada",
                    quantidade_kg="100.000",
                    data_movimento=date(2026, 8, 1),
                    referencia_externa=f"migration-0009-{sufixo}",
                    chave_idempotencia=f"migration-0009-movimento-{sufixo}",
                    operacao="credito_producao",
                    delta_fisico_kg="100.000",
                    delta_comprometido_kg="0.000",
                    snapshot_anterior={"saldo_fisico_kg": "0.000"},
                    snapshot_posterior={"saldo_fisico_kg": "100.000"},
                    criado_por=usuario,
                    lote=lote,
                    posicao=posicao,
                    origem=origem,
                )
                return movimento, posicao

            movimento_ativo, _ = criar_movimento_producao(
                lote=lote_ativo,
                sufixo="a",
            )
            movimento_cancelado, posicao_cancelada = criar_movimento_producao(
                lote=lote_cancelado,
                sufixo="c",
            )
            origem_estorno = Origem.objects.create(
                tipo="estorno",
                chave_idempotencia="migration-0009-origem-estorno",
                referencia_externa="migration-0009-estorno",
                hash_requisicao="e" * 64,
                metadados={"migration": "0009"},
                criado_por=usuario,
            )
            estorno = Movimento.objects.create(
                tipo="saida",
                quantidade_kg="100.000",
                data_movimento=date(2026, 8, 2),
                referencia_externa="migration-0009-estorno",
                chave_idempotencia="migration-0009-movimento-estorno",
                operacao="estorno",
                delta_fisico_kg="-100.000",
                delta_comprometido_kg="0.000",
                snapshot_anterior={"saldo_fisico_kg": "100.000"},
                snapshot_posterior={"saldo_fisico_kg": "0.000"},
                criado_por=usuario,
                lote=lote_cancelado,
                posicao=posicao_cancelada,
                origem=origem_estorno,
                estorno_de=movimento_cancelado,
            )

            def criar_carga(
                *, grupo, armazem, lote, fingerprint, contexto, movimentacao=None
            ):
                return Carga.objects.create(
                    grupo_colheita=grupo,
                    armazem=armazem,
                    lote=lote,
                    movimentacao=movimentacao,
                    criado_por=usuario,
                    data_colheita=date(2026, 8, 1),
                    placa="ABC1D23",
                    peso_bruto_kg="100.000",
                    umidade_percentual="12.00",
                    impureza_percentual="1.00",
                    defeitos_percentual="1.00",
                    desconto_total_percentual="0.000",
                    desconto_total_kg="0.000",
                    peso_liquido_kg="100.000",
                    sacas_60kg="1.667",
                    regra_desconto_aplicada={},
                    contexto_colheita=contexto,
                    fingerprint=fingerprint,
                )

            carga_ativa = criar_carga(
                grupo=grupo_ativo,
                armazem=armazem_grupo,
                lote=lote_ativo,
                movimentacao=movimento_ativo,
                contexto={"origem": "teste-ativo"},
                fingerprint="migration-0009-carga-ativa",
            )
            carga_cancelada = criar_carga(
                grupo=grupo_cancelado,
                armazem=armazem_grupo,
                lote=lote_cancelado,
                movimentacao=movimento_cancelado,
                contexto={"origem": "teste-cancelado"},
                fingerprint="migration-0009-carga-cancelada",
            )
            carga_divergente = criar_carga(
                grupo=grupo_divergente,
                armazem=armazem_saldo,
                lote=lote_divergente,
                contexto={"auditoria": "preservada"},
                fingerprint="migration-0009-carga-divergente",
            )

            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            apps = executor.loader.project_state([self.migrate_to]).apps
            CargaMigrada = apps.get_model("graos", "CargaColhida")
            GrupoMigrado = apps.get_model("graos", "GrupoColheita")

            ativa = CargaMigrada.objects.get(pk=carga_ativa.pk)
            self.assertEqual(ativa.status, "ativa")
            self.assertEqual(ativa.propriedade_id, propriedade_grupo.pk)
            self.assertEqual(ativa.cad_pro_id, cad_grupo.pk)
            self.assertEqual(ativa.cultura, "Soja")
            self.assertEqual(ativa.safra, "2026/2027")
            self.assertEqual(ativa.grupo_colheita_id, grupo_ativo.pk)
            self.assertEqual(ativa.contexto_colheita, {"origem": "teste-ativo"})

            cancelada = CargaMigrada.objects.get(pk=carga_cancelada.pk)
            self.assertEqual(cancelada.status, "cancelada")
            self.assertEqual(cancelada.cancelada_em, estorno.criado_em)
            self.assertEqual(cancelada.cancelada_por_id, usuario.pk)
            self.assertIn("já possuía estorno", cancelada.motivo_cancelamento)
            self.assertEqual(cancelada.grupo_colheita_id, grupo_cancelado.pk)

            divergente = CargaMigrada.objects.get(pk=carga_divergente.pk)
            self.assertEqual(divergente.status, "ativa")
            self.assertEqual(divergente.propriedade_id, propriedade_saldo.pk)
            self.assertEqual(divergente.cad_pro_id, cad_saldo.pk)
            self.assertEqual(divergente.cultura, "Milho")
            self.assertEqual(divergente.safra, "2027/2028")
            self.assertEqual(divergente.grupo_colheita_id, grupo_divergente.pk)
            self.assertEqual(divergente.contexto_colheita["auditoria"], "preservada")
            self.assertEqual(
                divergente.contexto_colheita["migracao_contexto_direto"],
                {
                    "versao": "graos.0009",
                    "origem": "armazem_e_lote",
                    "divergencias_grupo_legado": [
                        "propriedade/armazém",
                        "CAD/PRO/lote",
                        "cultura/lote",
                        "safra/lote",
                    ],
                },
            )
            self.assertEqual(CargaMigrada.objects.count(), 3)
            self.assertEqual(GrupoMigrado.objects.count(), 3)

            carga_direta = CargaMigrada.objects.create(
                grupo_colheita=None,
                propriedade_id=propriedade_grupo.pk,
                cad_pro_id=cad_grupo.pk,
                cultura="Soja",
                safra="2026/2027",
                armazem_id=armazem_grupo.pk,
                lote_id=lote_ativo.pk,
                criado_por_id=usuario.pk,
                data_colheita=date(2026, 8, 3),
                placa="XYZ9A87",
                peso_bruto_kg="80.000",
                umidade_percentual="12.00",
                impureza_percentual="1.00",
                defeitos_percentual="1.00",
                desconto_total_percentual="0.000",
                desconto_total_kg="0.000",
                peso_liquido_kg="80.000",
                sacas_60kg="1.333",
                regra_desconto_aplicada={},
                contexto_colheita={"origem": "carga-direta"},
                fingerprint="migration-0009-carga-direta",
            )

            with self.assertRaisesMessage(
                RuntimeError,
                "Não é seguro reverter graos.0009",
            ):
                MigrationExecutor(connection).migrate([self.migrate_from])

            self.assertIn(
                self.migrate_to,
                MigrationRecorder(connection).applied_migrations(),
            )
            self.assertTrue(
                CargaMigrada.objects.filter(
                    pk=carga_direta.pk,
                    grupo_colheita__isnull=True,
                ).exists()
            )
        finally:
            restaurador = MigrationExecutor(connection)
            restaurador.migrate(restaurador.loader.graph.leaf_nodes())
