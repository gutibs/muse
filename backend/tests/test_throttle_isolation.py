"""Los throttles no pueden frenar a la suite, y un test que los mide tiene
que poder fijar la rate que mide.

Las dos cosas dependen del mismo detalle: DRF evalúa
`THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` **en el cuerpo de la
clase**, o sea una referencia al dict que había al importar el módulo.
Reemplazar `settings.REST_FRAMEWORK` crea un dict nuevo que esa referencia
nunca ve, así que el override no toma efecto y los `ScopedRateThrottle` por
vista corren con las rates de producción.

Se descubrió construyendo F2.D: un test de throttle pasaba solo y fallaba en
la suite, según dónde cayera el import.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

# El import a nivel de módulo NO es decorativo: fuerza a que
# `rest_framework.throttling` se cargue durante la colección, que es cuando se
# carga en una suite real. Sin él, el módulo se importa dentro del test —con el
# conftest ya aplicado— y el test pasa por accidente. Ese es exactamente el
# síntoma que lo destapó: el mismo test pasaba solo y fallaba acompañado.
from rest_framework.throttling import SimpleRateThrottle  # noqa: F401


@pytest.mark.django_db
def test_los_throttles_no_frenan_a_los_tests():
	"""`register` son 5/hora en producción. Seis altas seguidas es algo que
	un test de registro puede hacer sin querer, y no debe recibir un 429 que
	no tiene nada que ver con lo que está probando."""
	url = reverse("register")
	client = APIClient()

	codigos = [
		client.post(
			url,
			data={
				"email": f"throttle{i}@example.com",
				"password": "Sup3r-strong-pass!",
				"displayName": f"Nº {i}",
				"acceptPrivacy": True,
			},
			format="json",
		).status_code
		for i in range(6)
	]

	assert 429 not in codigos, f"el override de rates no está aplicando: {codigos}"
