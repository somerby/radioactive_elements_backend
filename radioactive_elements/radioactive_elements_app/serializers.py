from .models import *
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = '__all__'

class ElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Element
        fields = '__all__'
        read_only_fields = ['element_id', 'status']

class ElementDecaySerializer(serializers.ModelSerializer):
    element = ElementSerializer(read_only=True)

    class Meta:
        model = Element_Decay
        fields = '__all__'
        read_only_fields = ['id', 'decay', 'element', 'remaining_quantity']

class DecaySerializer(serializers.ModelSerializer):
    elements = ElementDecaySerializer(many=True, read_only=True, source='decay_elements')
    creator = serializers.StringRelatedField()
    moderator = serializers.StringRelatedField()

    class Meta:
        model = Decay
        fields = '__all__'
        read_only_fields = ['decay_id', 'creator', 'moderator', 'status', 'date_of_creation', 'date_of_formation', 'date_of_finish']