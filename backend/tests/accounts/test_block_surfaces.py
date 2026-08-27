"""RF9-RF13 — el efecto del bloqueo en cada superficie que expone a otro.

Son las cinco que no heredan de ningún service, más `can_view`. Cada una tiene
su test porque cada una filtra por su cuenta: olvidarse de una deja el bloqueo
cosmético, que es el modo típico de fallar de esta feature.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Block, Friendship
from accounts.services.blocking import block_user, unblock_user
from feed.models import Activity
from pins.models import Pin
from tests.factories import PinFactory, RestaurantFactory, UserFactory


def _auth(user):
	client = APIClient()
	client.force_authenticate(user=user)
	return client


def _befriend(a, b):
	Friendship.objects.create(from_user=a, to_user=b, status=Friendship.Status.ACCEPTED)


def _review(user, restaurant, comment="Muy bueno"):
	return PinFactory(user=user, restaurant=restaurant, status="visited", rating=5, comment=comment)


# --- RF9: perfil y pins -----------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_a_blocked_user_cannot_see_the_profile_even_if_a_friendship_survives():
	"""`can_view` pasa por `are_friends`, que no sabe nada de bloqueos. Si una
	amistad sobreviviera —D-005 la recrea al registrarse con un email
	invitado— el perfil se seguiría viendo con un bloqueo puesto."""
	me, other = UserFactory(), UserFactory()
	_befriend(me, other)
	Block.objects.create(blocker=me, blocked=other)

	assert _auth(me).get(reverse("public_profile", kwargs={"user_id": other.id})).status_code == 403
	assert _auth(other).get(reverse("public_profile", kwargs={"user_id": me.id})).status_code == 403


@pytest.mark.critical
@pytest.mark.django_db
def test_a_blocked_user_cannot_list_the_others_pins():
	me, other = UserFactory(), UserFactory()
	_befriend(me, other)
	Block.objects.create(blocker=other, blocked=me)

	resp = _auth(me).get(reverse("user_pins", kwargs={"user_id": other.id}))

	assert resp.status_code == 403, resp.content


# --- RF10: búsqueda ---------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_search_hides_a_blocked_user_in_both_directions():
	me = UserFactory(username="searcher", email="searcher@example.com")
	other = UserFactory(username="hidden", email="hidden@example.com")
	other.profile.display_name = "Persona Buscada"
	other.profile.save()
	Block.objects.create(blocker=me, blocked=other)

	by_email = _auth(me).get(reverse("user_search"), {"q": other.email})
	by_name = _auth(me).get(reverse("user_search"), {"q": "Persona Buscada"})
	reverse_way = _auth(other).get(reverse("user_search"), {"q": me.email})

	assert by_email.json()["results"] == []
	assert by_name.json()["results"] == []
	assert reverse_way.json()["results"] == [], "también en la dirección contraria"


@pytest.mark.critical
@pytest.mark.django_db
def test_search_still_finds_everyone_else():
	me = UserFactory(username="searcher", email="searcher@example.com")
	findable = UserFactory(username="findable", email="findable@example.com")
	blocked = UserFactory(username="blocked", email="blocked@example.com")
	Block.objects.create(blocker=me, blocked=blocked)

	resp = _auth(me).get(reverse("user_search"), {"q": findable.email})

	assert [row["id"] for row in resp.json()["results"]] == [findable.id]


# --- RF11: feed -------------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_hides_a_blocked_friends_activity():
	me, friend, blocked = UserFactory(), UserFactory(), UserFactory()
	_befriend(me, friend)
	_befriend(me, blocked)
	PinFactory(user=friend)
	PinFactory(user=blocked)
	Block.objects.create(blocker=me, blocked=blocked)

	resp = _auth(me).get(reverse("feed"))

	actors = {row["actor"]["id"] for row in resp.json()["results"]}
	assert blocked.id not in actors
	assert friend.id in actors


@pytest.mark.critical
@pytest.mark.django_db
def test_feed_hides_an_activity_whose_target_is_blocked():
	me, friend, blocked = UserFactory(), UserFactory(), UserFactory()
	_befriend(me, friend)
	Block.objects.create(blocker=me, blocked=blocked)
	_befriend(friend, blocked)

	resp = _auth(me).get(reverse("feed"))

	targets = {
		(row["targetUser"] or {}).get("id")
		for row in resp.json()["results"]
		if row.get("targetUser")
	}
	assert blocked.id not in targets


# --- RF12: reseñas ----------------------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_reviews_hide_the_blocked_pair_but_not_for_a_third_party():
	a, b, c = UserFactory(), UserFactory(), UserFactory()
	restaurant = RestaurantFactory()
	_review(a, restaurant, "Reseña de A")
	_review(b, restaurant, "Reseña de B")
	Block.objects.create(blocker=a, blocked=b)
	url = reverse("restaurant-detail", kwargs={"pk": restaurant.pk})

	seen_by_a = {r["user"]["id"] for r in _auth(a).get(url).json()["reviews"]}
	seen_by_b = {r["user"]["id"] for r in _auth(b).get(url).json()["reviews"]}
	seen_by_c = {r["user"]["id"] for r in _auth(c).get(url).json()["reviews"]}

	assert b.id not in seen_by_a
	assert a.id not in seen_by_b
	assert seen_by_c == {a.id, b.id}, "D-001 sigue valiendo para terceros"


@pytest.mark.critical
@pytest.mark.slow
@pytest.mark.django_db
def test_blocking_does_not_shrink_the_review_list():
	"""El filtro va DENTRO de la query, antes del `[:20]`. Si se aplicara
	después del corte, quien bloqueó a alguien prolífico vería un puñado de
	reseñas en un restaurante que tiene decenas."""
	me = UserFactory()
	noisy = UserFactory()
	restaurant = RestaurantFactory()

	# 20 reseñas de terceros primero (quedan más viejas)...
	for i in range(20):
		_review(UserFactory(), restaurant, f"Reseña de un tercero {i}")
	# ...y 20 del que voy a bloquear, que son las más recientes.
	for i in range(20):
		other = UserFactory()
		_review(other, restaurant, f"Reseña ruidosa {i}")
		Block.objects.create(blocker=me, blocked=other)
	assert Pin.objects.filter(restaurant=restaurant).count() == 40

	resp = _auth(me).get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))

	reviews = resp.json()["reviews"]
	assert len(reviews) == 20, f"vio {len(reviews)} reseñas en vez de 20"
	assert all("ruidosa" not in r["comment"] for r in reviews)
	assert noisy  # noqa: B018 — mantiene la intención legible


# --- RF13: agregados de amigos ---------------------------------------------


@pytest.mark.critical
@pytest.mark.django_db
def test_friend_stats_ignore_a_blocked_friend():
	me, friend, blocked = UserFactory(), UserFactory(), UserFactory()
	restaurant = RestaurantFactory()
	_befriend(me, friend)
	_befriend(me, blocked)
	PinFactory(user=friend, restaurant=restaurant, status="visited", rating=2)
	PinFactory(user=blocked, restaurant=restaurant, status="visited", rating=5)
	Block.objects.create(blocker=me, blocked=blocked)

	stats = (
		_auth(me)
		.get(reverse("restaurant-detail", kwargs={"pk": restaurant.pk}))
		.json()["friendStats"]
	)

	assert stats["ratedCount"] == 1
	assert stats["ratingAvg"] == 2.0, "el rating del bloqueado no cuenta"


@pytest.mark.critical
@pytest.mark.django_db
def test_activity_of_a_blocked_user_is_filtered_not_deleted():
	"""El bloqueo es reversible: la actividad de pin se filtra al leer, no se
	borra, así que al desbloquear y volver a ser amigos reaparece. (Las de
	amistad sí se borran, que es RF3 — por eso hay que rehacer la amistad.)"""
	me, other = UserFactory(), UserFactory()
	_befriend(me, other)
	PinFactory(user=other)
	pin_activity = Activity.objects.get(actor=other, verb=Activity.Verb.PINNED)

	block_user(blocker=me, blocked=other)

	assert Activity.objects.filter(pk=pin_activity.pk).exists(), "la actividad no se borra"
	assert _auth(me).get(reverse("feed")).json()["results"] == []

	unblock_user(blocker=me, blocked=other)
	_befriend(me, other)

	resp = _auth(me).get(reverse("feed"))
	assert other.id in {row["actor"]["id"] for row in resp.json()["results"]}
