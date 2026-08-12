from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class GrupoColheitaMigration0006Tests(TransactionTestCase):
    migrate_from = ("graos", "0005_grupocolheita_cargacolhida_and_more")
    migrate_to = ("graos", "0006_grupocolheita_armazem_padrao")
    migrate_latest = ("graos", "0007_grupocolheita_observacoes")

    def test_carga_em_armazem_inativo_nao_define_padrao_invalido(self):
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
            cad_pro = CADPro.objects.create(
                codigo="MIG-0006",
                codigo_normalizado="MIG0006",
                descricao="Migration 0006",
            )
            inativo = Armazem.objects.create(
                propriedade=propriedade,
                nome="Silo inativo",
                capacidade_kg="1000",
                ativo=False,
            )
            ativo = Armazem.objects.create(
                propriedade=propriedade,
                nome="Silo ativo",
                capacidade_kg="1000",
                ativo=True,
            )
            lote = Lote.objects.create(
                armazem=inativo,
                cad_pro=cad_pro,
                codigo="MIG-LOTE",
                cultura="Soja",
                safra="2026/2027",
                classificacao_codigo="PADRAO",
            )
            grupo = Grupo.objects.create(
                propriedade=propriedade,
                cad_pro=cad_pro,
                criado_por=usuario,
                nome="Grupo migration",
                cultura="Soja",
                safra="2026/2027",
            )
            Carga.objects.create(
                grupo_colheita=grupo,
                armazem=inativo,
                lote=lote,
                criado_por=usuario,
                data_colheita="2026-08-01",
                placa="ABC1D23",
                peso_bruto_kg="100",
                umidade_percentual="10",
                impureza_percentual="1",
                defeitos_percentual="1",
                desconto_total_percentual="0",
                desconto_total_kg="0",
                peso_liquido_kg="100",
                sacas_60kg="1.667",
                regra_desconto_aplicada={},
                fingerprint="migration-0006-inativo",
            )

            executor = MigrationExecutor(connection)
            executor.migrate([self.migrate_to])
            apps = executor.loader.project_state([self.migrate_to]).apps
            GrupoMigrado = apps.get_model("graos", "GrupoColheita")
            self.assertEqual(
                GrupoMigrado.objects.get(pk=grupo.pk).armazem_padrao_id,
                ativo.pk,
            )
        finally:
            MigrationExecutor(connection).migrate([self.migrate_latest])
