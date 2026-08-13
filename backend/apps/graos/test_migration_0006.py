from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class GrupoColheitaMigration0006Tests(TransactionTestCase):
    migrate_from = ("graos", "0005_grupocolheita_cargacolhida_and_more")
    migrate_to = ("graos", "0006_grupocolheita_armazem_padrao")
    migrate_latest = ("graos", "0007_grupocolheita_observacoes")

    def test_apenas_armazenagem_historica_ativa_da_propriedade_e_usada(self):
        executor = MigrationExecutor(connection)
        try:
            executor.migrate([self.migrate_from])
            apps = executor.loader.project_state([self.migrate_from]).apps
            Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
            Propriedade = apps.get_model("propriedades", "Propriedade")
            CADPro = apps.get_model("cadpro", "CADPro")
            Armazem = apps.get_model("graos", "ArmazemGraos")
            Lote = apps.get_model("graos", "LoteGraos")
            Grupo = apps.get_model("graos", "GrupoColheita")
            Carga = apps.get_model("graos", "CargaColhida")

            usuario = Usuario.objects.create(username="migration-grupo-0006")
            propriedade = Propriedade.objects.create(
                nome="Fazenda Migration",
                municipio="Sorriso",
                uf="MT",
                area_hectares="100",
            )
            outra_propriedade = Propriedade.objects.create(
                nome="Fazenda Externa Migration",
                municipio="Sorriso",
                uf="MT",
                area_hectares="100",
            )
            cad_pro = CADPro.objects.create(
                codigo="MIG-0006",
                codigo_normalizado="MIG0006",
                descricao="Migration 0006",
            )
            seguro = Armazem.objects.create(
                propriedade=propriedade,
                nome="Silo histórico seguro",
                capacidade_kg="1000",
                ativo=True,
            )
            inativo = Armazem.objects.create(
                propriedade=propriedade,
                nome="Silo histórico inativo",
                capacidade_kg="1000",
                ativo=False,
            )
            externo = Armazem.objects.create(
                propriedade=outra_propriedade,
                nome="Silo histórico externo",
                capacidade_kg="1000",
                ativo=True,
            )

            def criar_grupo(nome):
                return Grupo.objects.create(
                    propriedade=propriedade,
                    cad_pro=cad_pro,
                    criado_por=usuario,
                    nome=nome,
                    cultura="Soja",
                    safra="2026/2027",
                )

            def criar_carga(grupo, armazem, indice):
                lote = Lote.objects.create(
                    armazem=armazem,
                    cad_pro=cad_pro,
                    codigo=f"MIG-LOTE-{indice}",
                    cultura="Soja",
                    safra="2026/2027",
                    classificacao_codigo="PADRAO",
                )
                Carga.objects.create(
                    grupo_colheita=grupo,
                    armazem=armazem,
                    lote=lote,
                    criado_por=usuario,
                    data_colheita="2026-08-01",
                    placa=f"ABC1D2{indice}",
                    peso_bruto_kg="100",
                    umidade_percentual="10",
                    impureza_percentual="1",
                    defeitos_percentual="1",
                    desconto_total_percentual="0",
                    desconto_total_kg="0",
                    peso_liquido_kg="100",
                    sacas_60kg="1.667",
                    regra_desconto_aplicada={},
                    fingerprint=f"migration-0006-{indice}",
                )

            grupo_seguro = criar_grupo("Grupo histórico seguro")
            criar_carga(grupo_seguro, seguro, 1)
            grupo_inativo = criar_grupo("Grupo histórico inativo")
            criar_carga(grupo_inativo, inativo, 2)
            grupo_externo = criar_grupo("Grupo histórico externo")
            criar_carga(grupo_externo, externo, 3)
            grupo_sem_historico = criar_grupo("Grupo sem histórico")

            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            apps = executor.loader.project_state([self.migrate_to]).apps
            GrupoMigrado = apps.get_model("graos", "GrupoColheita")
            valores = {
                item.pk: item.armazem_padrao_id
                for item in GrupoMigrado.objects.filter(
                    pk__in=(
                        grupo_seguro.pk,
                        grupo_inativo.pk,
                        grupo_externo.pk,
                        grupo_sem_historico.pk,
                    )
                )
            }
            self.assertEqual(valores[grupo_seguro.pk], seguro.pk)
            self.assertIsNone(valores[grupo_inativo.pk])
            self.assertIsNone(valores[grupo_externo.pk])
            self.assertIsNone(valores[grupo_sem_historico.pk])
        finally:
            restaurador = MigrationExecutor(connection)
            restaurador.migrate(restaurador.loader.graph.leaf_nodes())
