"""La URL de reserva la puede escribir cualquier usuario que da de alta un
restaurante, y después se le muestra como botón a todos los demás. Eso la
convierte en un canal de phishing si se acepta a ciegas: "reservá acá" es
justamente el contexto donde alguien entrega datos sin mirar el dominio.

Se aprueban solas tres cosas: los proveedores conocidos, el sitio oficial que
Google ya nos dio, y un dominio que lleva el nombre del restaurante. Todo lo
demás queda pendiente y no se dibuja hasta que una persona lo mire.
"""

import pytest
from django.core.exceptions import ValidationError

from restaurants.models import Restaurant
from restaurants.services.reservations import classify_reservation_url
from tests.factories import RestaurantFactory


@pytest.mark.critical
@pytest.mark.parametrize(
	"url,provider",
	[
		("https://www.opentable.com/r/bar-nacional", Restaurant.ReservationProvider.OPENTABLE),
		("https://thefork.com/restaurant/bar-nacional", Restaurant.ReservationProvider.THEFORK),
		("https://resy.com/cities/ny/bar-nacional", Restaurant.ReservationProvider.RESY),
		(
			"https://bar-nacional.sevenrooms.com/reservations",
			Restaurant.ReservationProvider.SEVENROOMS,
		),
		# Los tres de abajo entraron con evidencia de venues reales del
		# catálogo, no por catálogo teórico: Woki es el que usan Anchoita y
		# Trescha en Buenos Aires, Tock el de Yardbird en Hong Kong, y
		# CoverManager aparece en la región. Sin ellos, un link legítimo de
		# esos proveedores cae en la cola de revisión.
		("https://www.wokiapp.com/restaurante/bar-nacional", Restaurant.ReservationProvider.WOKI),
		("https://www.exploretock.com/bar-nacional/", Restaurant.ReservationProvider.TOCK),
		(
			"https://www.covermanager.com/reserve/module_restaurant/bar-nacional",
			Restaurant.ReservationProvider.COVERMANAGER,
		),
		# Meitre da un subdominio por restaurante, no un path.
		("https://barnacional.meitre.com/", Restaurant.ReservationProvider.MEITRE),
	],
)
def test_known_providers_are_approved(url, provider):
	result = classify_reservation_url(url, name="Bar Nacional", website="")

	assert result.provider == provider
	assert result.status == Restaurant.ReservationStatus.APPROVED


@pytest.mark.critical
def test_the_official_site_is_approved():
	"""`website` viene del payload de Google, no del usuario."""
	result = classify_reservation_url(
		"https://barnacional.com.ar/reservas",
		name="Bar Nacional",
		website="https://www.barnacional.com.ar/",
	)

	assert result.provider == Restaurant.ReservationProvider.DIRECT
	assert result.status == Restaurant.ReservationStatus.APPROVED


@pytest.mark.critical
def test_a_domain_carrying_the_restaurant_name_is_approved():
	result = classify_reservation_url(
		"https://reservas.barnacional.com/", name="Bar Nacional", website=""
	)

	assert result.status == Restaurant.ReservationStatus.APPROVED


@pytest.mark.critical
@pytest.mark.parametrize(
	"url",
	[
		# El nombre en el path no dice nada del dueño del dominio.
		"https://evil.example/reservar/bar-nacional",
		# Ni en la query.
		"https://evil.example/?r=bar-nacional",
		# Ni un dominio que apenas se le parece al del proveedor.
		"https://opentable.evil.example/r/bar-nacional",
		# Ni un subdominio del atacante con el proveedor adentro.
		"https://www.opentable.com.evil.example/r/bar-nacional",
	],
)
def test_lookalike_urls_stay_pending(url):
	result = classify_reservation_url(url, name="Bar Nacional", website="")

	assert result.status == Restaurant.ReservationStatus.PENDING
	assert result.provider == Restaurant.ReservationProvider.OTHER


@pytest.mark.critical
@pytest.mark.parametrize(
	"url",
	["javascript:alert(1)", "ftp://files.example/x", "data:text/html,<script>"],
)
def test_non_http_schemes_are_refused(url):
	with pytest.raises(ValidationError):
		classify_reservation_url(url, name="Bar Nacional", website="")


@pytest.mark.django_db
def test_saving_a_restaurant_classifies_the_url():
	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://www.opentable.com/r/bar-nacional"
	)

	restaurant.refresh_from_db()
	assert restaurant.reservation_provider == Restaurant.ReservationProvider.OPENTABLE
	assert restaurant.reservation_status == Restaurant.ReservationStatus.APPROVED


@pytest.mark.django_db
def test_a_manual_approval_survives_an_unrelated_save():
	"""Si cada save reclasificara, aprobar a mano en el admin no serviría de
	nada: el siguiente guardado lo mandaría de vuelta a la cola."""
	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://reservas.example/bar"
	)
	assert restaurant.reservation_status == Restaurant.ReservationStatus.PENDING

	restaurant.reservation_status = Restaurant.ReservationStatus.APPROVED
	restaurant.save()
	restaurant.city = "Montevideo"
	restaurant.save()

	restaurant.refresh_from_db()
	assert restaurant.reservation_status == Restaurant.ReservationStatus.APPROVED


@pytest.mark.django_db
def test_changing_the_url_sends_it_back_to_the_queue():
	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://reservas.example/bar"
	)
	restaurant.reservation_status = Restaurant.ReservationStatus.APPROVED
	restaurant.save()

	restaurant.reservation_url = "https://otro-sitio.example/bar"
	restaurant.save()

	restaurant.refresh_from_db()
	assert restaurant.reservation_status == Restaurant.ReservationStatus.PENDING


@pytest.mark.django_db
def test_clearing_the_url_clears_the_provider():
	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://www.opentable.com/r/bar-nacional"
	)

	restaurant.reservation_url = ""
	restaurant.save()

	restaurant.refresh_from_db()
	assert restaurant.reservation_provider == ""
	assert restaurant.reservation_status == Restaurant.ReservationStatus.PENDING


@pytest.mark.critical
@pytest.mark.django_db
def test_the_api_hides_a_reservation_url_pending_review():
	"""Mientras no pasó la clasificación, para la API no existe: si saliera,
	el botón se dibujaría igual y la revisión no serviría de nada."""
	from rest_framework.test import APIRequestFactory

	from restaurants.serializers import RestaurantSerializer
	from tests.factories import UserFactory

	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://cualquier-cosa.example/bar"
	)
	request = APIRequestFactory().get("/")
	request.user = UserFactory()

	data = RestaurantSerializer(restaurant, context={"request": request}).data

	assert data["reservation"] is None
	assert "reservation_url" not in data


@pytest.mark.django_db
def test_the_api_exposes_an_approved_reservation_url():
	from rest_framework.test import APIRequestFactory

	from restaurants.serializers import RestaurantSerializer
	from tests.factories import UserFactory

	restaurant = RestaurantFactory(
		name="Bar Nacional", reservation_url="https://www.opentable.com/r/bar-nacional"
	)
	request = APIRequestFactory().get("/")
	request.user = UserFactory()

	data = RestaurantSerializer(restaurant, context={"request": request}).data

	assert data["reservation"] == {
		"url": "https://www.opentable.com/r/bar-nacional",
		"provider": "opentable",
	}


@pytest.mark.critical
@pytest.mark.django_db
def test_a_user_can_submit_a_reservation_url_but_it_is_not_published():
	"""El alta la hace cualquier usuario. La URL se guarda y queda en la cola;
	la respuesta no la devuelve."""
	from django.urls import reverse
	from rest_framework.test import APIClient

	from tests.factories import UserFactory

	client = APIClient()
	client.force_authenticate(user=UserFactory())

	resp = client.post(
		reverse("restaurant-list"),
		{
			"name": "Bar Nacional",
			"latitude": -34.6,
			"longitude": -58.38,
			"reservationUrl": "https://phishing.example/bar-nacional",
		},
		format="json",
	)

	assert resp.status_code == 201, resp.content
	assert resp.json()["reservation"] is None
	created = Restaurant.objects.get(name="Bar Nacional")
	assert created.reservation_url == "https://phishing.example/bar-nacional"
	assert created.reservation_status == Restaurant.ReservationStatus.PENDING


@pytest.mark.django_db
def test_a_non_http_reservation_url_is_a_400_not_a_500():
	from django.urls import reverse
	from rest_framework.test import APIClient

	from tests.factories import UserFactory

	client = APIClient()
	client.force_authenticate(user=UserFactory())

	resp = client.post(
		reverse("restaurant-list"),
		{
			"name": "Bar Nacional",
			"latitude": -34.6,
			"longitude": -58.38,
			"reservationUrl": "javascript:alert(1)",
		},
		format="json",
	)

	assert resp.status_code == 400, resp.content
