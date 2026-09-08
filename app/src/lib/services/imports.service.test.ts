import { describe, expect, it } from 'vitest';
import { resolvedRows, unresolvedRows, type ImportJob } from './imports.service';

const job = (report: ImportJob['report']): ImportJob => ({
	id: 1,
	source: 'lista.csv',
	state: 'ready',
	total: report.length,
	processed: report.length,
	matched: 0,
	failed: 0,
	report,
	createdAt: ''
});

describe('qué filas se pueden pinear', () => {
	it('las encontradas, vengan del catálogo o de Google', () => {
		const j = job([
			{ row: 2, name: 'A', outcome: 'catalogue', restaurantId: 1 },
			{ row: 3, name: 'B', outcome: 'imported', restaurantId: 2 }
		]);
		expect(resolvedRows(j).map((r) => r.restaurantId)).toEqual([1, 2]);
	});

	it('una fila encontrada sin id no se ofrece', () => {
		// Sin restaurante no hay nada que pinear, y mostrarla como elegible
		// daría un checkbox que no hace nada.
		const j = job([{ row: 2, name: 'A', outcome: 'catalogue', restaurantId: null }]);
		expect(resolvedRows(j)).toEqual([]);
	});

	it('las que no se resolvieron se muestran aparte, no se esconden', () => {
		// Si el archivo tenía 50 y entran 47, la persona tiene que ver cuáles
		// tres faltaron y por qué.
		const j = job([
			{ row: 2, name: 'A', outcome: 'catalogue', restaurantId: 1 },
			{ row: 3, name: 'B', outcome: 'not_found' },
			{ row: 4, name: 'C', outcome: 'ambiguous' },
			{ row: 5, name: '', outcome: 'unreadable' }
		]);
		expect(unresolvedRows(j).map((r) => r.outcome)).toEqual([
			'not_found',
			'ambiguous',
			'unreadable'
		]);
	});

	it('las pendientes no cuentan como problema: todavía no se miraron', () => {
		const j = job([{ row: 2, name: 'A', outcome: 'pending' }]);
		expect(unresolvedRows(j)).toEqual([]);
		expect(resolvedRows(j)).toEqual([]);
	});
});
