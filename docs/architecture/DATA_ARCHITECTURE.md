# Arquitectura de dados

Raw immutable → reported facts → normalized facts → resolved series → metrics → assessment/valuation → snapshots.

Cada transformação guarda versão, timestamps, origem, estado de qualidade e lineage. Os dados corrigidos não apagam os anteriores. Consultas point-in-time respeitam `available_at`.
