# F2.A — Tres niveles de privacidad por pin

**Estado: listo para implementar (2026-08-27).** Toca permisos, así que por
regla del proyecto va mini-spec previa y TDD. Las cuatro decisiones de
producto que lo bloqueaban las **cerró Jess el 2026-08-27** y están abajo con
su respuesta.

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

## Las cuatro decisiones, cerradas por Jess (2026-08-27)

**1 — D-001 pasa a valer para los pins públicos.** Que son el default, así
que la propuesta de valor no se mueve: las reseñas siguen siendo públicas
salvo que su autor decida otra cosa. `docs/PRODUCT_DECISIONS.md` se actualiza
en el mismo commit que la implementación.

**2 — El promedio del restaurante incluye los pins privados.** El número
queda estable e igual para todos los que miran la ficha, en vez de depender
de quién es el viewer. El `Count("pins")` que va al lado cuenta sobre el
mismo universo, para que promedio y conteo no queden con denominadores
distintos.

**2.bis — `get_friend_stats` es la excepción y NO incluye privados.**
Derivada de la anterior, decidida junto con ella. El promedio "de tus
amigos" se calcula sobre pocos datos: con un solo amigo pineado, ese número
*es* el rating de esa persona, así que incluir un pin privado ahí lo
publicaría. Sólo entran los pins de amigos que el viewer puede ver.

**3 — Un pin privado no entra en una lista compartida, ni curada ni `auto`.**
El criterio queda parejo: privado es sólo para el dueño, en toda superficie.
Elegirlo a mano no lo convierte en compartible; si se lo quiere en una lista,
primero se le cambia el nivel.

**4 — El feed filtra el pin que pasó a privado.** Aunque la `Activity` ya
haya ocurrido y el amigo ya la haya visto. Es lo coherente con el punto 3 y
con lo que el feed ya hace hoy: `feed/serializers.py:10` serializa el pin en
su estado actual, así que un comentario editado ya se ve actualizado en una
actividad vieja.

## Testing

TDD, y los invariantes que van marcados `@pytest.mark.critical`:

- Un pin `private` no aparece en: reseñas del restaurante, feed de un amigo,
  perfil de un amigo, ni en una lista compartida — **tampoco en una `curated`
  donde el dueño lo eligió a mano** (decisión 3).
- Una `Activity` cuyo pin pasó a `private` desaparece del feed del amigo que
  antes la veía (decisión 4).
- El promedio y el conteo de la ficha del restaurante **no cambian** cuando
  un pin pasa a `private`: dan lo mismo para el dueño, un amigo y un
  desconocido (decisión 2).
- `get_friend_stats` **sí** cambia: el pin privado de un amigo no entra en
  ese promedio (decisión 2.bis). Con un único amigo pineado y su pin en
  `private`, la ficha no devuelve stats de amigos.
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
