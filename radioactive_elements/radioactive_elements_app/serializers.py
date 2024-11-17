from .models import *
from rest_framework import serializers
from collections import OrderedDict

class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'is_staff', 'is_superuser']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 

class ElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Element
        fields = '__all__'
        read_only_fields = ['element_id', 'status']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 

class ElementForDecaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Element
        fields = ['element_id', 'name', 'status', 'img_url']
        read_only_fields = ['element_id', 'status']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 

class ElementDecaySerializer(serializers.ModelSerializer):
    element = ElementForDecaySerializer(read_only=True)

    class Meta:
        model = Element_Decay
        fields = '__all__'
        read_only_fields = ['id', 'decay', 'element', 'remaining_quantity']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 

class DecaySerializer(serializers.ModelSerializer):
    elements = ElementDecaySerializer(many=True, read_only=True, source='decay_elements')
    creator = serializers.StringRelatedField()
    moderator = serializers.StringRelatedField()

    class Meta:
        model = Decay
        fields = '__all__'
        read_only_fields = ['decay_id', 'creator', 'moderator', 'status', 'date_of_creation', 'date_of_formation', 'date_of_finish']

        def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields 