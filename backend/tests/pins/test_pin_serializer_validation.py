import pytest

from pins.serializers import PinSerializer
from tests.factories import RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_serializer_validates_status_rating():
	user = UserFactory()
	restaurant = RestaurantFactory()
	base = {"restaurant": restaurant.id}

	# Case 1: to_visit + rating → invalid (cannot rate something you have not visited)
	s1 = PinSerializer(data={**base, "status": "to_visit", "rating": 5})
	assert not s1.is_valid()
	assert "rating" in s1.errors

	# Case 2: visited without rating → invalid
	s2 = PinSerializer(data={**base, "status": "visited"})
	assert not s2.is_valid()
	assert "rating" in s2.errors

	# Case 3: visited + rating → valid
	s3 = PinSerializer(data={**base, "status": "visited", "rating": 4})
	assert s3.is_valid(), s3.errors

	# Case 4: to_visit without rating → valid
	s4 = PinSerializer(data={**base, "status": "to_visit"})
	assert s4.is_valid(), s4.errors

	# (touch user var so linters don't complain; the user is not strictly
	# required because PinSerializer.create injects request.user, but the
	# audit listed it as part of the test setup.)
	assert user.pk is not None
