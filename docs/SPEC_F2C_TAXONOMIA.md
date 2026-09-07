# F2.C — Filtro multi-atributo, hashtags privados y colecciones

Estado: **listo para implementar** (2026-09-07). Salió de discovery con tres
decisiones que redujeron el bloque; la trazabilidad está en § 9.

---

## 1 · Problema

El catálogo tiene 556 restaurantes y hoy sólo se puede filtrar por nombre,
ciudad y cocina. La taxonomía para filtrar mejor **ya está cargada** —501 de
esos 556 tienen etiquetas de vibe, ocasión y ambiente— pero no hay forma de
usarla: alguien que quiere "un lugar tranquilo para una cena romántica" tiene
que leer la lista entera. Del otro lado, quien ya guardó 151 pins tampoco puede
acotarlos: encontrar algo propio cuesta tanto como descubrir algo nuevo.

Y falta un lugar para lo que ninguna taxonomía cerrada va a cubrir: que alguien
marque sus propios pins con "con Jess" o "viaje a Bangkok".

## 2 · Usuarios y casos de uso

**Un solo rol: la persona que usa la app.** No hay caso de administrador ni de
moderación en este bloque.

- Busca en el catálogo cruzando ejes: romántico **y** para cena **y** vegetariano.
- Acota sus propios pins con los mismos ejes, sobre el mapa.
- Marca pins con etiquetas propias que sólo ve ella, y filtra por ellas.
- Agrupa pins elegidos a mano bajo un título, para sí misma o para compartir.

## 3 · Requisitos funcionales

**Filtro multi-atributo**

- **RF1.** `RestaurantFilterSet` acepta un parámetro por eje: `vibe`,
  `occasion`, `scene` y `dietary`. Cada uno toma valores separados por coma.
- **RF2.** Dentro de un eje, los valores son **OR**: `?vibe=romantic,quiet`
  devuelve los que tengan cualquiera de las dos.
- **RF3.** Entre ejes distintos, son **AND**: `?vibe=romantic&occasion=date-night`
  devuelve sólo los que tengan las dos. Criterio de aceptación: un restaurante
  con `romantic` pero sin `date-night` **no** aparece.
- **RF4.** Los ejes se combinan con los filtros que ya existen (`search`,
  `city`, `cuisine`, `insider`) y con `nearby`, sin perder ninguno.
- **RF5.** Un valor inexistente (`?vibe=no-existe`) devuelve cero resultados, no
  un error ni la lista completa.
- **RF6.** El endpoint de pins acepta los mismos cuatro ejes, filtrando por las
  etiquetas **del restaurante** de cada pin.

**Hashtags privados**

- **RF7.** Una persona puede asociar etiquetas de texto libre a sus pins.
- **RF8.** Un hashtag pertenece a quien lo creó. Dos personas pueden tener el
  mismo texto sin verse ni compartir fila.
- **RF9.** Al guardar se normaliza: se saca el `#`, pasa a minúsculas y se
  convierte a slug. `#DateNight`, `#datenight` y `#date night` son el mismo.
- **RF10.** Tope de 30 caracteres por hashtag y de 10 por pin. Pasarse es un 400
  con mensaje, no un truncado silencioso.
- **RF11.** Los hashtags **nunca** salen en una lista compartida ni en ningún
  endpoint público. Criterio de aceptación: un test que abra una lista
  compartida de alguien con hashtags y verifique que no aparecen.
- **RF12.** El endpoint de pins filtra por hashtag propio.
- **RF13.** Borrar la cuenta se lleva los hashtags: son datos personales.

**Colecciones**

- **RF14.** No se crea ningún modelo nuevo. Las colecciones son
  `SharedList(kind=curated)`, que ya tiene título, items ordenados (`position`) y
  nota por item.

## 4 · Requisitos no funcionales

- **Rendimiento.** El AND entre ejes agrega un join por eje. Con cuatro ejes
  activos son cuatro joins sobre una tabla M2M de 556 filas: aceptable, pero la
  consulta debe salir con `distinct()` y sin N+1 en la serialización.
- **Privacidad.** Los hashtags son el primer dato del proyecto que es
  **explícitamente privado y de nadie más**: no viaja a amigos, no viaja a
  listas compartidas, no viaja a analytics.
- **i18n.** Los mensajes de error nuevos pasan por `gettext_lazy` y se traducen
  a es e it, como exige el test guardián del proyecto.
- **Mobile.** El selector de filtros es un bottom sheet: cuatro ejes por N
  valores no entran en 390 px de ancho.

## 5 · Fuera de alcance

- **Hashtags visibles o compartidos.** Se decidió que sean privados. Hacerlos
  públicos abre texto libre de usuario hacia terceros, con la moderación que eso
  implica — el mismo problema que el plan ya marcó para el nombre del votante en
  F2.D.
- **Un modelo `Collection` propio.** Sería una segunda implementación al lado de
  las listas curadas.
- **Hashtags en el catálogo.** Filtrar restaurantes por hashtags ajenos exigiría
  agregarlos entre usuarios, que es justo lo que los hace privados.
- **Tocar `Pin.tags`.** Existe, tiene UI y no lo usó nadie (0 de 210). Se deja
  como está y se decide con datos del beta.
- **Autoselección de vibe desde Google.** Depende del SKU de Places, que sigue
  sin confirmarse.

## 6 · Edge cases

| Caso | Severidad | Manejo |
|---|---|---|
| `?vibe=romantic&vibe=quiet` (parámetro repetido en vez de coma) | importante | Se toma la última ocurrencia, que es el comportamiento de django-filter. No se inventa un merge. |
| Un solo `tags__slug__in` para todos los ejes | **crítico** | Es el bug que convierte el AND en OR **sin fallar**: el filtro miente y devuelve de más. Un join por eje, con un test que lo fije. |
| Hashtag que queda vacío al normalizar (`#`, `###`) | importante | 400 con mensaje. No se guarda una fila con slug vacío. |
| Dos personas con el mismo hashtag | importante | Filas distintas, únicas por `(user, slug)`. Ninguna ve la de la otra. |
| Hashtag en un pin que pasa a privado | menor | No cambia nada: los hashtags ya son privados en cualquier nivel del pin. |
| Filtro combinado con `nearby` | importante | Ambos van por `filter_queryset`, que es lo que el bloque 0 dejó preparado. Test que los combine. |
| 10 hashtags y se agrega el 11 | importante | 400 con el tope dicho en el mensaje. |

## 7 · Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El AND silencioso (OR encubierto) | **alta** | alto: el filtro devuelve de más y nadie lo nota | Test explícito con un restaurante que tenga un solo eje |
| Los hashtags se filtran a una lista compartida | media | alto: es lo único que prometemos privado | Test sobre el serializer público, del lado del endpoint anónimo |
| El bottom sheet no entra en 390 px con 20 etiquetas | media | medio | Scroll interno por eje, no lista única |
| `Pin.tags` sin usar confunde al usuario junto a los hashtags | media | bajo | Queda anotado, se decide con el beta |

## 8 · Stack propuesto

- **django-filter**, ampliando `RestaurantFilterSet`. Su docstring ya dice que el
  filtro multi-atributo de fase 2 es una adición a esa clase y no un segundo
  mecanismo al lado: se respeta.
- **`CommaSeparatedFilter`**, que ya existe en el módulo para `cuisine` y da OR
  dentro del eje. No se escribe uno nuevo.
- **Modelo `Hashtag(user, slug, name)`** con M2M a `Pin`, único por
  `(user, slug)`. **Descartado** reusar `Tag` con un `kind=personal`: metería
  filas por usuario en una tabla que hoy es catálogo global y compartido, y
  cualquier consulta de tags tendría que acordarse de excluirlas — la misma
  clase de bug que la revisión de F2.E encontró en los campos del perfil ajeno.

## 9 · Trazabilidad

| RF / decisión | Origen |
|---|---|
| RF1–RF5 (ejes, OR/AND) | `PLAN_FASES.md` § F2.C, y el docstring de `restaurants/filters.py` |
| RF6 y el filtro en el mapa | Respuesta del usuario: "Buscar y el mapa" |
| RF7–RF13 (hashtags privados) | Respuesta del usuario: "Sí, pero privados" |
| RF11 (nunca en lo público) | Verificado en el código: `serializers_public.py` sirve los tags del pin, así que sin esta regla los hashtags saldrían solos |
| RF14 (sin modelo nuevo) | Respuesta del usuario: "Son lo mismo: ampliar las listas" |
| Filtro sobre el catálogo y no sobre `Pin.tags` | Verificado en la base: 501/556 restaurantes con tags, 0/210 pins |
| Tope de 10 hashtags por pin | `[ASSUMPTION]` — no se habló del número. Sale de que el plan pide "tope de largo y cantidad" sin decir cuál |
| Tope de 30 caracteres | `[ASSUMPTION]` — mismo origen |
| Bottom sheet en vez de `<select>` | `PLAN_FASES.md` § F2.C y las reglas mobile-first del `CLAUDE.md` |

Dos ASSUMPTION sobre nueve items: 22%, bajo el umbral que obligaría a otra
ronda de clarify. Las dos son números que se cambian en una línea.

## Sugerencias fuera de scope

- **`Pin.tags` sin uso.** 0 de 210 pins tienen etiquetas propias, con la UI
  construida y en producción. O el lugar no se entiende, o la gente no quiere
  etiquetar sus pins. Vale mirarlo con el beta antes de sumarle hashtags al lado.
- **Los 55 restaurantes sin tags** del catálogo van a ser invisibles para
  cualquier filtro por eje. Conviene saber cuáles son antes de que alguien
  reporte que "faltan lugares".
