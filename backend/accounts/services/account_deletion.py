"""Right-to-erasure pipeline (GDPR art. 17, PDPO DPP 2).

Single entry point for deleting a user account. Deliberately NOT a
`user.delete()`: per D-009 the account is anonymised so that public reviews
survive without an identity, because D-001 makes those reviews the product's
value proposition. A hard delete would silently empty out every restaurant
page the person ever contributed to.

What survives: Pin rows (status, rating, comment, visited_at) and the User row
they hang off, scrubbed of every identifying field.
What is destroyed: profile fields, avatar file, friendships in both
directions, invitations sent by and addressed to the user, feed activity,
shared list links, and consent records.
"""

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from accounts.models import ConsentRecord, EmailInvitation, Friendship
from feed.models import Activity
from pins.models import SharedList

logger = logging.getLogger(__name__)

ANONYMOUS_EMAIL_DOMAIN = "muse.local"


@transaction.atomic
def anonymise_user(user) -> None:
	"""Irreversibly strip `user` of identity, keeping their reviews readable.

	Atomic: a failure halfway through must not leave an account that is
	half-erased and still logged in.
	"""
	original_email = user.email
	placeholder = f"deleted-{uuid.uuid4()}@{ANONYMOUS_EMAIL_DOMAIN}"

	# Social graph and anything addressed to the person. Invitations are
	# matched on the ORIGINAL email — after the swap there is nothing to match.
	Friendship.objects.filter(from_user=user).delete()
	Friendship.objects.filter(to_user=user).delete()
	EmailInvitation.objects.filter(from_user=user).delete()
	if original_email:
		EmailInvitation.objects.filter(email__iexact=original_email).delete()
	Activity.objects.filter(actor=user).delete()
	Activity.objects.filter(target_user=user).delete()
	SharedList.objects.filter(user=user).delete()
	ConsentRecord.objects.filter(user=user).delete()

	profile = user.profile
	if profile.avatar:
		# delete(save=False) removes the file from storage; the field is
		# cleared with the explicit save below.
		profile.avatar.delete(save=False)
	profile.avatar = ""
	profile.display_name = ""
	profile.bio = ""
	profile.city = ""
	profile.website = ""
	profile.instagram = ""
	profile.phone = ""
	profile.location = None
	profile.favourite_cuisine = None
	profile.deleted_at = timezone.now()
	profile.dietary_preferences.clear()
	profile.save()

	# Identity last: once this lands the account can no longer authenticate,
	# which also invalidates every outstanding JWT (simplejwt rejects inactive
	# users at authentication time).
	user.username = placeholder
	user.email = placeholder
	user.first_name = ""
	user.last_name = ""
	user.is_active = False
	user.set_unusable_password()
	user.save()

	logger.info("Account erased (user_id=%s)", user.id)
