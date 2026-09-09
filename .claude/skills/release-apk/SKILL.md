---
name: release-apk
description: Procedimiento completo para compilar y publicar el APK de Muse — elegir el número de versión, correr el script de bump, buildear contra producción, firmar, verificar dentro del APK y regenerar los iconos de launcher si cambió la marca. Usar cuando se pida un build de APK, una release de Android, subir a Play Store, o cambiar el ícono de la app.
argument-hint: [major|minor|patch]
allowed-tools: Read Grep Glob Bash(npm run:*) Bash(npx cap:*) Bash(cat:*) Bash(ls:*) Bash(grep:*) Bash(unzip:*) Bash(cp:*) Bash(git:*) Bash(./gradlew:*)
---

# Release del APK de Muse

Verificado contra el código el 2026-09-09: `versionCode 27`, `versionName "V1.6.0"`,
`app/package.json` en `"1.6.0"`. **No asumas que sigue siendo ése** — leelo antes de nada.

## Tres reglas que rompen producción si se ignoran

**1 · Para distribución siempre `npm run build:apk-prod`. Nunca `build:apk`.**

- `build:apk-prod` usa `.env.capacitor-prod` → `https://lovemuse.app/api/v1`
- `build:apk` usa `.env.capacitor` → `https://muse.dothecode.com/api/v1`, que es la URL de dev

Un APK distribuido con `build:apk` apunta al backend de desarrollo, y eso no se nota
hasta que alguien lo instala. Por eso la verificación de abajo es dentro del APK.

**2 · El número de versión lo calcula `npm run bump:<nivel>`, no vos a mano.**

`app/scripts/bump-version.mjs` es la única fuente de la lógica: lee `build.gradle`,
calcula el semver, incrementa el `versionCode` y escribe **los dos archivos
sincronizados** (`build.gradle` con la `V`, `package.json` sin ella, porque npm exige
semver estricto). El 2026-08-21 se editaron a mano y quedó consistente de casualidad.

**3 · Para la store se compila `bundleRelease` (.aab). El APK es para probar a mano.**

Play Store **no acepta APK** para apps nuevas: exige Android App Bundle. Todo lo de
abajo produce un `.apk`, que sirve para instalar en tu teléfono con `adb` y para
mandárselo a alguien, **no para publicar**. Cuando las cuentas estén aprobadas:

```bash
cd app/android
JAVA_HOME=/opt/homebrew/opt/openjdk@21 ./gradlew bundleRelease
# sale en app/build/outputs/bundle/release/app-release.aab
```

Verificado el 2026-09-09 con la V1.6.0: el comando corre, usa el mismo keystore que
`assembleRelease` —el bundle sale firmado, `META-INF/MUSE.RSA` adentro— y pesa
**16,6 MB contra los 28,3 MB del APK**, antes de que Play descarte las ABIs que
sobran. El nombre del archivo **no** lleva la versión, a diferencia del APK: si vas
a guardar varios, renombralo vos.

**Esto no es un detalle de formato, cambia el tamaño.** Desde la V1.6.0 el APK lleva
`libbarhopper_v3.so` —el motor nativo de ML Kit, que usa el escáner de QR de F2.F— en
**cuatro** arquitecturas, y el APK pasó de 7 MB a 28,3 MB. De esos, **11,6 MB son x86
y x86_64, que sólo corren en emuladores**: ningún teléfono los ejecuta.

- Con `.aab` el problema desaparece solo: Play le entrega a cada teléfono su
  arquitectura y nada más.
- Mientras la distribución sea a mano, para no mandar 11,6 MB de relleno, en
  `app/android/app/build.gradle`, dentro de `defaultConfig`:
  ```gradle
  ndk { abiFilters 'arm64-v8a', 'armeabi-v7a' }
  ```
  **Verificalo recompilando y mirando el APK**, no asumas el ahorro:
  `unzip -l $APK | grep libbarhopper`.

## Elegir el número: `V<major>.<minor>.<patch>`

- **major** — rompe compatibilidad o es un pivote de producto.
- **minor** — feature visible al usuario, cambio de endpoint, o cambio de assets que
  afecta la UX (icono, splash, naming).
- **patch** — bugfix sobre el minor actual.

No inventes saltos: después de `V0.1.2` va `V0.1.3`, no `V0.2.0`.

**Si no hubo cambio de frontend desde el último APK, no bumpees**: rebuildeá la misma
versión. Un fix server-side no cambia lo que corre en el teléfono. Para saberlo:

```bash
BUMP=$(git log --oneline -S'"version": "<versión actual>"' -- app/package.json | tail -1 | cut -d' ' -f1)
git diff --name-only $BUMP..HEAD -- app/src app/android
```

**Avisale al usuario qué versión vas a compilar antes de compilarla.**

## Pasos

```bash
cd app
npm test && npm run check      # 148 tests + svelte-check. No compiles sobre rojo.
npm run bump:minor             # o patch/major. Sólo si cambió el frontend.
npm run build:apk-prod         # bundle SvelteKit contra lovemuse.app
npx cap sync android           # copia el bundle Y registra los plugins nativos
cd android
JAVA_HOME=/opt/homebrew/opt/openjdk@21 ./gradlew assembleRelease
```

`build:apk-prod` corre **sólo** el `vite build`. `cap sync` y `gradlew` van aparte: no
los encadena ningún script, y saltarlos deja un APK con el bundle viejo adentro.

**`cap sync` modifica archivos versionados** (`capacitor.settings.gradle`,
`capacitor.build.gradle`) cuando hay plugins nuevos. Commitealos: sin ellos, un build
limpio desde el repo compila la app sin el plugin, y el síntoma es una feature que
simplemente no existe en el teléfono con todo el backend sano. Pasó con
`capacitor-push-notifications` en la V1.4.0.

El build necesita `VITE_CARTO_KEY` disponible: alcanza con tenerla en `app/.env` (Vite
lo carga también en los modos de Capacitor). **No la pongas en `.env.capacitor-prod`**:
ese archivo está versionado. Si falta, el build corta a propósito — sin la key CARTO
devuelve 200 igual, pero con "API KEY REQUIRED" estampado sobre cada mapa, y eso recién
se ve con el APK instalado.

**El keystore de release ya existe.** `app/android/keystore.properties` está en su lugar
y `assembleRelease` produce un APK firmado con `CN=Muse, O=Muse, L=Hong Kong`. Para
distribuir se compila **release**, nunca debug.

**Salida**: `app/android/app/build/outputs/apk/release/muse-V<X.Y.Z>-release.apk`. El
nombre lo arma Gradle con `variant.outputFileName`, así no se pisan APKs entre versiones.

## Verificá dentro del APK, no en `build/`

Lo que se distribuye es el APK, y `cap sync` puede fallar sin avisar:

```bash
APK=app/android/app/build/outputs/apk/release/muse-V<X.Y.Z>-release.apk
unzip -o -q $APK -d /tmp/apk "assets/public/*"
grep -rl lovemuse.app /tmp/apk        # tiene que dar >0
grep -rl muse.dothecode /tmp/apk      # tiene que dar 0

AAPT=$(ls -d ~/Library/Android/sdk/build-tools/*/aapt2 | tail -1)
$AAPT dump badging $APK | grep -E "^package|uses-permission"

SIGNER=$(ls -d ~/Library/Android/sdk/build-tools/*/apksigner | tail -1)
$SIGNER verify --print-certs $APK | grep "certificate DN"
```

`versionCode` y `versionName` del `dump badging` son los reales del APK — si no coinciden
con `build.gradle`, algo del pipeline no corrió.

Después: copiar el APK a `~/Desktop/` e instalar con
`adb install -r`, que conserva sesión e idioma.

**Lo que ninguna de estas verificaciones cubre**: que la cámara abra y que el escáner
de F2.F lea un QR de verdad. `@capacitor-mlkit/barcode-scanning` no tiene
implementación web, así que en el navegador la pantalla contesta `unsupported` y en
los tests el plugin está mockeado. Es el mismo hueco que tuvieron los canales de
notificación en la V1.4.0: sólo se ve con el APK instalado.

## El número que muestra Ajustes

Sale de `__APP_VERSION__`, inyectado en build time desde `package.json`.
`app/src/lib/app-version.test.ts` lo compara contra `package.json` y `build.gradle`, así
que los tres no pueden divergir. **Falso positivo conocido**: el dev server de Vite
inyecta ese valor al arrancar, así que después de un bump muestra el número viejo hasta
que se reinicia. No es un bug del APK.

## Iconos de launcher (sólo si cambió la marca)

- Source de marca: `app/src/lib/assets/logo_muse.png`.
- Destino: `app/android/app/src/main/res/mipmap-{ldpi,mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/`,
  y cada una de esas seis carpetas lleva **cuatro** PNG: `ic_launcher.png`,
  `ic_launcher_round.png`, `ic_launcher_foreground.png` e `ic_launcher_background.png`.
  Son **24 archivos**, más los dos XML de `mipmap-anydpi-v26`.
- Color del adaptive icon: `app/android/app/src/main/res/values/ic_launcher_background.xml`,
  hoy `#FFFFFF`.
- **No hay script versionado que los regenere** (verificado el 2026-09-07). Usá una
  herramienta que los produzca de una — no los edites a mano densidad por densidad.

## Diagnóstico: "el usuario ve una versión vieja"

El `versionName` es la fuente de verdad humana. Si el celular muestra `V1.3.0` y el APK
actual es `V1.4.0`, tiene un APK viejo: que desinstale y reinstale **antes** de seguir
diagnosticando cualquier otra cosa. No busques el bug en el código hasta descartar eso,
pero tampoco lo asumas sin preguntarle qué versión tiene.
