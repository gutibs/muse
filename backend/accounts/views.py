from rest_framework import generics, permissions, status
from rest_framework.response import Response

from accounts.serializers import (
	ChangePasswordSerializer,
	ProfileSerializer,
	RegisterSerializer,
)


class RegisterView(generics.CreateAPIView):
	serializer_class = RegisterSerializer
	permission_classes = (permissions.AllowAny,)

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = serializer.save()
		return Response(result, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
	serializer_class = ProfileSerializer

	def get_object(self):
		return self.request.user.profile


class ChangePasswordView(generics.GenericAPIView):
	serializer_class = ChangePasswordSerializer

	def post(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		request.user.set_password(serializer.validated_data["new_password"])
		request.user.save()
		return Response(status=status.HTTP_204_NO_CONTENT)
