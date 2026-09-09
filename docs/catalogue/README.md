# Carga del catálogo curado

El cuello de botella de Muse no es código: son los restaurantes. Al 2026-09-09
el catálogo tiene 57 filas y **11 de Hong Kong**, que es el mercado del
producto, con la taxonomía en cero (0 con vibe, 0 con occasion, 1 con scene).
Sin restaurantes, "cerca mío" no responde y el filtro de F2.C —que ya está
construido y probado en el backend— sería una pantalla que siempre dice "sin
resultados".

La lista la arma **Jess**, que vive en Hong Kong y tiene el criterio de qué
lugar vale la pena. Acá está lo que se le pide y en qué formato.

## Los archivos

| Archivo | Para qué |
|---|---|
| `BRIEF_JESS.md` | El texto para mandarle. En inglés. Explica las columnas y las 26 etiquetas con su significado. |
| `muse-catalogue-template.xlsx` | La plantilla. Hoja 1 (`Restaurants`) con los encabezados y vacía; hoja 2 con el vocabulario y una fila de ejemplo. |
| `muse-catalogue-template.csv` | Lo mismo en CSV, con tres filas de ejemplo que hay que reemplazar. |

**La hoja 1 va vacía a propósito.** `imports/services/parse.py` lee
`libro.active`, así que si los ejemplos quedaran ahí se importarían como si
fueran recomendaciones de ella, con etiquetas que puso el programador. El
ejemplo vive en la hoja de referencia, donde el parser no lo ve.

## Qué hace el importador con cada columna

- `name` y `city` resuelven la fila. La ciudad matchea **por contención**, no
  por igualdad: el catálogo tiene "Hong Kong", "Hong Kong Island" y "Kowloon"
  para la misma ciudad porque `city` sale del payload de Google, y exigir
  igualdad mandaba a pagar dos llamadas por lugares que ya teníamos.
- `district` entra en la consulta a Google, que es lo que distingue dos
  sucursales del mismo nombre. Hoy `Goodin' Out Coffee` está dos veces en el
  catálogo con ciudades distintas. No se guarda en el modelo: ese campo lo
  llena `google_place_parser` con el `sublocality` del payload.
- `tags` se aplican **sólo si ese import dio de alta el lugar**, o si nadie lo
  describió todavía. Nunca pisan lo que otra persona escribió:
  `restaurants/views.py::_check_owner_or_staff` ya establece que nadie edita un
  restaurante ajeno, y el import no puede ser la puerta de atrás de esa regla.
  Se pueden mandar en una columna `tags` o en columnas por eje (`vibe`,
  `occasion`, `scene`, `dietary`): todas se juntan, porque los slugs son únicos
  en la tabla entera.

**"Descrito" se mide sobre vibe y occasion**, los dos ejes que Google no da por
ningún camino. Las etiquetas de `scene` que infiere `google_import` —terraza,
música en vivo, acepta perros— no bloquean: si contaran, correr
`backfill_from_google --attributes` dejaría el catálogo entero cerrado a la
lista curada sin que nadie relacione una cosa con la otra.

## Vocabulario

Las 26 etiquetas que se le ofrecen salen de `restaurants_tag` y son las que el
filtro de F2.C cruza (OR dentro de cada eje, AND entre ejes). Queda afuera
`recommended`, que es `kind=highlight`: un destacado editorial, no una
descripción del lugar.

Si Jess propone una etiqueta que no existe, **se agrega al vocabulario** — la
lista actual se sembró por migración y no salió de nadie que use la app.
