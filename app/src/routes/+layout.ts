// Muse es una SPA: `adapter-static` con `fallback: index.html`, y el HTML que
// se publica es un shell vacío que el cliente hidrata. El SSR nunca corrió en
// producción, pero `vite dev` sí lo intenta al entrar directo a una URL, y ahí
// el código que toca `localStorage` o `navigator` explota en Node — un 500 al
// abrir /restaurant/30 a mano, mientras que llegando por navegación interna
// andaba. Declararlo acá hace que dev y prod hagan lo mismo.
export const ssr = false;
