# Sprint 12 — Aplicativo

## Status

Concluída em 25/07/2026. A versão funcional 1.0 está completa.

## Entregas

- Progressive Web App instalável em navegadores compatíveis;
- manifesto, identidade visual e modo standalone;
- service worker com cache do aplicativo e dos recursos estáticos;
- navegação adaptada a telas pequenas;
- indicador online/offline e ação de instalação;
- fallback do shell quando a rede não estiver disponível;
- exclusão explícita de `/api/` do cache, evitando persistir JWT ou dados
  operacionais sensíveis.

Operações que consultam ou alteram dados continuam exigindo conexão. O cache
offline preserva apenas a estrutura visual e recursos públicos. Não há
dependência nova, publicação em loja ou serviço pago.
