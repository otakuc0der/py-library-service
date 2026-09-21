from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "password",
            "is_staff",
        ]
        read_only_fields = [
            "id",
            "is_staff",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "style": {
                    "input_type": "password",
                },
            },
        }

    def create(
        self,
        validated_data: dict[str, Any],
    ) -> User:
        return get_user_model().objects.create_user(
            **validated_data,
        )

    def update(
        self,
        instance: User,
        validated_data: dict[str, Any],
    ) -> User:
        password = validated_data.pop("password", None)

        user = super().update(
            instance=instance,
            validated_data=validated_data,
        )

        if password:
            user.set_password(password)
            user.save(
                update_fields=["password"],
            )

        return user


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email"]
        read_only_fields = fields
