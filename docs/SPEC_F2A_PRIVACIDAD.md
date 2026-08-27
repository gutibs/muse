# F2.A — Tres niveles de privacidad por pin

**Estado: borrador para revisar.** Toca permisos, así que por regla del
proyecto va mini-spec previa y TDD. Hay cuatro decisiones de producto sin
tomar, marcadas como **ABIERTA** más abajo; ninguna línea de código antes de
cerrarlas.

Base: mapeo exhaustivo del backend (2026-08-21) sobre quién lee un pin hoy.

---

## El problema

Hoy un pin tiene **dos visibilidades distintas a la vez, según por dónde se
lo mire**, y ninguna la eligió su dueño:

- En el perfil y en el feed es **para amigos** (`UserPinsView` y `FeedView`
  filtran por amistad).
- En la ficha del restaurante su reseña es **para cualquier usuario
  logueado**: `get_reviews` (`restaurants/serializers.py:241`) no filtra por
  identidad, y eso es deliberado — es la decisión **D-001**, "las reseñas son
  la propuesta de valor".

Quien escribe "fui con mi psicóloga, un desastre" en un comentario no tiene
forma de saber que eso lo ve todo el padrón, ni de evitarlo.

## Lo que hay que cubrir

El mapeo encontró **21 puntos** que leen pins. Seis muestran contenido a
alguien que no es el dueño **sin ninguna noción de privacidad**:

| # | Punto | Hoy lo ve |
|---|---|---|
| 13 | `restaurants/serializers.py:241` `get_reviews` | cualquier usuario logueado |
| 15 | `restaurants/views.py:41` `Avg("pins__rating")` | cualquier usuario logueado |
| 16 | `restaurants/views.py:42` `Count("pins")` | cualquier usuario logueado |
| 12 | `feed/serializers.py:10` pin dentro de la Activity | amigos |
| 6 | `pins/serializers_public.py:111` lista compartida `auto` | **anónimo con el link** |
| 7 | `pins/serializers_public.py:102` lista curada | **anónimo con el link** |

Y dos más que filtran cardinalidad aunque no muestren contenido:

- **#10** `accounts/serializers.py:78-80` — los contadores del perfil
  (`pinCount`, `visitedCount`, `toVisitCount`) cuentan **todos** los pins del
  usuario. Un amigo vería "42 lugares" aunque sólo pueda ver 30.
- **#14** `restaurants/serializers.py:225` `get_friend_stats` — con un solo
  amigo, el promedio *es* el rating de ese amigo.

Los cuatro puntos de admin (#18–#21) quedan como están: staff ve todo, y eso
es lo esperable.

## Modelo

```
Pin.visibility          → NULL | public | friends | private
Profile.default_pin_visibility → public | friends | private
```

`Pin.visibility` **nullable a propósito**: NULL significa "lo que diga mi
default", así que cambiar la preferencia del perfil mueve los pins que nunca
se tocaron uno por uno, y respeta los que sí.

**El default global tiene que ser `public`.** Cualquier otro valor cambia la
visibilidad de los 211 pins que ya existen y vacía las fichas de restaurante
de un día para el otro. Esto no es una preferencia, es la condición para no
romper lo que hay.

## Dónde se implementa

En **`accounts/services/visibility.py`** y **`pins/selectors.py`**, que el
bloque 0 dejó preparados para exactamente esto — el docstring de
`visibility.py` ya dice que es el módulo que cambia cuando existan niveles
por pin.

Dos funciones nuevas, y el resto de las superficies pasan a usarlas:

- `visible_pin_filter(viewer)` → un `Q` reutilizable: los pins públicos, más
  los de amigos marcados `friends`, más todos los propios.
- `visible_pins(viewer, owner=...)` lo aplica, así los dos llamadores
  actuales lo heredan sin cambios.

Los seis puntos ciegos se enganchan de a uno, cada uno con su test.

## Las cuatro decisiones abiertas

**ABIERTA 1 — ¿Qué pasa con D-001?** Los tres niveles la contradicen de
frente. La salida natural: D-001 pasa a valer **para los pins públicos**, que
son el default, y el autor puede restringir el suyo. Eso mantiene la
propuesta de valor y le da la perilla a quien escribe. Si se elige esto,
`docs/PRODUCT_DECISIONS.md` se actualiza en el mismo commit.

**ABIERTA 2 — ¿Un pin privado cuenta en el promedio del restaurante?**
Excluirlo es coherente ("privado es privado"), pero hace que el promedio del
restaurante dependa de quién mira. Incluirlo mantiene un número estable y no
revela nada individual, aunque con dos reseñas el promedio delata bastante.

**ABIERTA 3 — ¿Se puede poner un pin privado en una lista curada?** Elegirlo
a mano para una lista es un acto explícito de compartirlo, así que
probablemente sí, y el nivel no debería estorbar. Lo que sí parece claro es
que una lista `auto` (por filtro) **no** debe publicar pins privados:
compartir un filtro no es elegir cada pin.

**ABIERTA 4 — ¿El feed muestra un pin que pasó a privado?** La `Activity` ya
ocurrió y el amigo quizás ya la vio. Filtrarlo es más consistente; dejarlo es
más barato. Con `feed/serializers.py:10` serializando el pin **en su estado
actual**, hoy el comentario editado se ve actualizado en una actividad vieja,
así que filtrar es el camino coherente con lo que ya hace.

## Testing

TDD, y los invariantes que van marcados `@pytest.mark.critical`:

- Un pin `private` no aparece en: reseñas del restaurante, feed de un amigo,
  perfil de un amigo, ni en una lista compartida `auto`.
- Un pin `friends` aparece para un amigo y no para un desconocido, en las
  seis superficies.
- Un pin sin `visibility` (NULL) se comporta según el default del perfil.
- Cambiar el default del perfil **no** pisa los pins que tienen valor propio.
- Los contadores del perfil cuentan lo que el viewer puede ver, no más.
- El dueño siempre se ve todo lo suyo.

## Verificación end-to-end

Además de la suite: crear tres pins con los tres niveles en la base local
(que tiene el snapshot de producción), y recorrer con dos cuentas —una amiga
y una desconocida— las seis superficies, más el link compartido desde una
ventana anónima.
