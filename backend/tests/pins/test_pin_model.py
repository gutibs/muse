"""Model-level guarantee that Pin status<->rating invariant runs on every
save, including direct ORM writes that bypass PinSerializer.

Pre-fix, Pin.clean() existed but full_clean() was never called, so any
caller using Pin.objects.create / instance.save with invalid combos
persisted bad data. The fix wires Pin.save() to full_clean() first.
The serializer-level test (test_pin_serializer_validates_status_rating)
already covers the API boundary; this test covers the model boundary.
"""

import pytest
from django.core.exceptions import ValidationError

from pins.models import Pin
from tests.factories import RestaurantFactory, UserFactory


@pytest.mark.critical
@pytest.mark.django_db
def test_pin_model_save_validates_status_rating():
	user = UserFactory()
	restaurant = RestaurantFactory()

	# visited without rating → ValidationError
	with pytest.raises(ValidationError) as exc:
		Pin.objects.create(
			user=user,
			restaurant=restaurant,
			status=Pin.Status.VISITED,
		)
	assert "rating" in exc.value.message_dict

	# to_visit with rating → ValidationError
	with pytest.raises(ValidationError) as exc:
		Pin.objects.create(
			user=user,
			restaurant=RestaurantFactory(),
			status=Pin.Status.TO_VISIT,
			rating=4,
		)
	assert "rating" in exc.value.message_dict

	# Valid: visited + rating → persists
	pin = Pin.objects.create(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.VISITED,
		rating=4,
	)
	assert pin.id is not None

	# Valid: to_visit without rating → persists
	pin2 = Pin.objects.create(
		user=user,
		restaurant=RestaurantFactory(),
		status=Pin.Status.TO_VISIT,
	)
	assert pin2.id is not None

	# Update flips an existing pin from to_visit to visited without setting
	# rating → save() must reject it (covers the "edit a pin via direct
	# attribute mutation" path).
	pin2.status = Pin.Status.VISITED
	with pytest.raises(ValidationError) as exc:
		pin2.save()
	assert "rating" in exc.value.message_dict
