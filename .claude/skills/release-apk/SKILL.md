---
name: release-apk
description: Procedimiento completo para compilar y publicar el APK de Muse — elegir el número de versión, actualizar los dos archivos que lo declaran, buildear contra producción y regenerar los iconos de launcher si cambió la marca. Usar cuando se pida un build de APK, una release de Android, subir a Play Store, o cambiar el ícono de la app.
argument-hint: [major|minor|patch]
allowed-tools: Read Grep Glob Bash(npm run:*) Bash(cat:*) Bash(ls:*)
---

# Release del APK de Muse

Verificado contra el código el 2026-08-11: `versionCode 15`, `versionName "V1.0.0"`, `app/package.json` en `"1.0.0"`.

## Regla que rompe producción si se ignora

**Para distribución siempre `npm run build:apk-prod`. Nunca `build:apk`.**

- `build:apk-prod` usa `.env.capacitor-prod` → `https://lovemuse.app/api/v1`
- `build:apk` usa `.env.capacitor` → `https://muse.dothecode.com/api/v1`, que es la URL de dev

Un APK distribuido con `build:apk` apunta al backend de desarrollo. Verificá el modo antes de subir nada.

## Elegir el número: `V<major>.<minor>.<patch>`

- **major** — rompe compatibilidad o es un pivote de producto.
- **minor** — feature visible al usuario, cambio de endpoint, o cambio de assets que afecta la UX (icono, splash, naming).
- **patch** — bugfix sobre el minor actual.

No inventes saltos: después de `V0.1.2` va `V0.1.3`, no `V0.2.0`, salvo que el cambio sea claramente "important".

## Pasos

1. **Leé el valor actual** en `app/android/app/build.gradle` (`versionName` y `versionCode`). No asumas cuál es.
2. **Decidí el siguiente** según las reglas de arriba. Si el usuario pasó `major`/`minor`/`patch` como argumento, usá eso.
3. **Actualizá los dos archivos en el mismo commit** — si divergen, el APK y npm declaran versiones distintas:
   - `app/android/app/build.gradle` → `versionName "V1.1.0"` y `versionCode` incrementado en 1. El `versionCode` es un entero monotónico y **Play Store lo exige**: si no sube, rechaza el upload.
   - `app/package.json` → `"version": "1.1.0"` — sin la `V`, porque npm exige semver estricto.
4. **Buildeá** con `npm run build:apk-prod` desde `app/`.

   Necesita `VITE_CARTO_KEY` disponible: alcanza con tenerla en `app/.env` (Vite
   lo carga también en los modos de Capacitor), o pasándola en la línea:

   ```
   VITE_CARTO_KEY=<la key> npm run build:apk-prod
   ```

   **No la pongas en `.env.capacitor-prod`**: ese archivo está versionado. Si
   falta, el build corta con un mensaje que lo explica — es a propósito: sin la
   key CARTO devuelve 200 igual, pero con "API KEY REQUIRED" estampado sobre
   cada mapa, y eso recién se ve con el APK instalado en un teléfono.

## Pendiente conocido

El APK `V1.0.0` compilado **es anterior al borrado de cuenta**. Play Store exige esa funcionalidad para toda app con registro, así que hay que rebuildear antes de publicar. Por la convención sería `V1.1.0`: es una feature visible al usuario.

## Iconos de launcher (sólo si cambió la marca)

- Source de marca: `app/src/lib/assets/logo_muse.png`.
- Destino: `app/android/app/src/main/res/mipmap-{ldpi,mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/`, y cada una de esas seis carpetas lleva **cuatro** PNG: `ic_launcher.png`, `ic_launcher_round.png`, `ic_launcher_foreground.png` e `ic_launcher_background.png`. Son **24 archivos**, más los dos XML de `mipmap-anydpi-v26`.
- Color del adaptive icon: `app/android/app/src/main/res/values/ic_launcher_background.xml`, hoy `#FFFFFF`.
- Si actualizás el logo, **regenerá los 24 assets con una herramienta**. No los edites a mano densidad por densidad.

## Diagnóstico: "el usuario ve una versión vieja"

El `versionName` es la fuente de verdad humana. Si el celular de un usuario muestra `V0.1.0` y el APK actual es `V0.1.2`, tiene un APK viejo instalado: que desinstale y reinstale **antes** de seguir diagnosticando cualquier otra cosa. No busques el bug en el código hasta descartar eso, pero tampoco lo asumas sin preguntarle qué versión tiene.
