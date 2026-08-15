# Infraestructura de Muse (producción)

Referenciado desde `CLAUDE.md`. Leer antes de desplegar, tocar AWS o diagnosticar una caída.

## Máquinas

- **EC2** `t3.small` Ubuntu 24.04 — IP fija `3.129.56.80`, disco raíz 20 GiB.
  Era de 8 GiB y **se llenó el 2026-08-04**: el deploy murió en el `git pull` y el sitio quedó caído. Si volvés a rozar el límite, mirá `/var/lib/containerd`.
- **RDS** `db.t3.micro` PostgreSQL 16 — endpoint `database-1.c1yuu8ceyjpj.us-east-2.rds.amazonaws.com`
- **SG EC2** (`muse-ec2-sg`): 22 (0.0.0.0/0 — intencional, para GitHub Actions), 80, 443
- **SG RDS** (`muse-rds-sg`): 5432 sólo desde `muse-ec2-sg`
- **Dominio y SSL**: `lovemuse.app` con Certbot, servido por nginx (`nginx/default-aws.conf`)
- **Redis**: container en el mismo EC2 (`docker-compose.aws.yml`), `maxmemory 256mb`,
  política `allkeys-lru`, sin persistencia. **No** es ElastiCache: a este volumen no
  justifica los ~USD 10/mes del nodo más chico. Migrar es cambiar `REDIS_URL` en el
  `.env` — cero código. Ojo: el deploy hace `down` + `up -d`, así que la caché se vacía
  en cada push. Es caché, se repuebla sola; el efecto visible es que el primer minuto
  después de un deploy vuelve a pegarle a Google.
- **Media** (avatares, y después las fotos de Places cacheadas): volumen nombrado
  `muse_media` en el disco del EC2, montado read-only en nginx, que lo sirve en
  `/media/`. **No** hay S3 ni CloudFront, y no hacen falta: el catálogo entero del beta
  son ~300 MB sobre 20 GiB ya pagos, y a este volumen un CDN cuesta lo mismo que servir
  directo (~USD 1/mes las dos opciones). S3 se justifica el día que haya más de una
  instancia compartiéndolo.
  Los avatares estaban rotos en prod por dos razones que se arreglaron juntas: el
  contenedor no declaraba ningún volume (el deploy hace `down` + `up -d`, y sin volumen
  nombrado eso borra el filesystem) y `default-aws.conf` no tenía `location /media/`,
  así que `MEDIA_ROOT` sólo se servía con `DEBUG`. **Vigilar el disco**: ya se llenó una
  vez, y ahora las fotos cacheadas crecen ahí.

## Deploy

Push a `main` → GitHub Actions → SSH al EC2.

**El orden importa: `build` primero, con los contenedores todavía arriba; recién después `down` + `up -d`.** Al revés —que era como estaba— cualquier fallo del build dejaba producción caída. `set -e` corta antes del `down`, así que un build roto es un deploy en rojo con el sitio intacto.

Tres detalles que ya mordieron:

- **Bug de docker-compose 1.29.2**: hacer `down && up`, nunca sólo `up`.
- **`command_timeout: 30m`** en la acción SSH. Un build sin cache no entra en los 10 minutos por defecto y la sesión se corta a mitad de camino.
- **El prune de imágenes va al final y con `--filter until=720h`.** Un `docker image prune -af` sin filtro se lleva las capas intermedias sin tag de las que depende el cache del builder clásico (compose v1 no usa BuildKit) y fuerza un build completo en el deploy siguiente.

## Configuración

- **Secrets en GitHub**: `EC2_HOST`, `EC2_SSH_KEY`
- **Vars de entorno**: en `/home/ubuntu/muse/.env` en el server, no en el repo. Una var nueva se agrega también a `.env.example` en el mismo commit.

## Pendiente

La imagen del backend instala `requirements/dev.txt`: pytest, ipython y debug-toolbar viajan a producción y pesan **~1.75 GB**.
