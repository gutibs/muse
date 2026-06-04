"""Current versions of the data-protection policies users must consent to at
registration. Bump the relevant value when the corresponding legal text
changes (see nginx/landing/{gdpr,pdpo}.html and app/src/routes/legal/...);
a new version means existing users would need to re-consent if/when we add a
re-consent flow. Date-based so the version maps to a concrete published text.
"""

from accounts.models import ConsentRecord

POLICY_VERSIONS = {
	ConsentRecord.Policy.GDPR: "2026-05-28",
	ConsentRecord.Policy.PDPO: "2026-05-28",
}
