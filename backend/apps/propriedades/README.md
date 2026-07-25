# Módulo de Propriedades

Responsável pelo cadastro de propriedades, validações, upload KML, cálculo de
centroide e API REST.

## Organização

- `models.py`: entidade `Propriedade`;
- `serializers.py`: validação de entrada e persistência;
- `kml_service.py`: leitura segura e cálculo do centroide;
- `services.py`: atualização das coordenadas;
- `views.py`: CRUD autenticado, busca, ordenação e exclusão protegida;
- `tests.py`: testes funcionais da API.

O módulo não depende de `fastkml` ou `shapely`; a leitura usa a biblioteca padrão
do Python. Consulte a documentação pública em `docs/api/README.md`.
