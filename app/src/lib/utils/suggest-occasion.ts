/**
 * Ocasión sugerida según el día y la hora.
 *
 * Es una sugerencia sobre el gusto de alguien, no un hecho como la terraza,
 * así que la pantalla la marca visualmente como tal y se quita con un toque.
 * Dos salvaguardas más viven en quien la usa: nunca en la pantalla de
 * edición, donde pisaría una elección ya hecha, y nunca en un pin de "quiero
 * ir" — guardar un lugar al mediodía no dice nada sobre cuándo pensás ir.
 *
 * Devuelve `null` cuando la hora no dice nada. Es la respuesta más común y
 * es la correcta: adivinar de más molesta más de lo que ayuda.
 */
export function suggestOccasion(now: Date = new Date()): string | null {
	const day = now.getDay(); // 0 domingo … 6 sábado
	const hour = now.getHours();
	const weekend = day === 0 || day === 6;

	if (hour >= 22 || hour < 4) return 'drinks-bar';
	if (weekend && hour >= 9 && hour < 13) return 'brunch';
	if (!weekend && hour >= 12 && hour < 15) return 'business-lunch';
	// Viernes y sábado a la noche. El resto de la semana una cena es una
	// cena, y no hay por qué suponer una cita.
	if ((day === 5 || day === 6) && hour >= 19 && hour < 22) return 'date-night';
	return null;
}
