import factory


class BaseFactory(factory.django.DjangoModelFactory):
	class Meta:
		abstract = True
