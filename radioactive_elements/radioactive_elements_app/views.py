from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.contrib.auth import authenticate, logout
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import *
from .serializers import *
from .minio import deleteImg, addImg
from .hl_calc import HalfLifeCalculation
from .permissions import IsManager, IsAdmin, AuthBySSID, IsAuth
from .redis import session_storage

from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import uuid

def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes        
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)
        return decorated_func
    return decorator

@csrf_exempt
@swagger_auto_schema(method='post', request_body=SwaggerCustomUserSerializer)
@api_view(['post'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data["email"] 
    password = request.data["password"]
    user = authenticate(request, email=username, password=password)
    if user is not None:
        random_key = str(uuid.uuid4())
        session_storage.set(random_key, username)

        response = Response({'status': 'ok'}, status=status.HTTP_200_OK)
        response.set_cookie("session_id", random_key)

        return response
    else:
        return Response({'status': 'error', 'error': 'login failed'}, status=status.HTTP_403_FORBIDDEN)

@csrf_exempt
@swagger_auto_schema(method='post')
@api_view(['post'])
@authentication_classes([AuthBySSID])
@permission_classes([IsAuth])
def logout_view(request):
    ssid = request.COOKIES.get("session_id")
    session_storage.delete(ssid)
    logout(request)
    return Response({'status': 'logged out'}, status=status.HTTP_200_OK)

def getDecayInformation(user):
    decay = user.user_decays.all().filter(status='draft').first()
    if decay is None:
        decay_elements_count = 0 
        decay_id = 0
    else:
        decay_elements_count = Element_Decay.objects.filter(decay_id=decay.decay_id).count()
        decay_id = decay.decay_id

    return {'decay_elements_count': decay_elements_count, 
            'decay_id': decay_id}

class elementsMethods(APIView):
    serializer = ElementSerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([AllowAny])
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'atomic_mass',
            openapi.IN_QUERY,
            description='Атомная масса',
            type=openapi.TYPE_INTEGER
        )
    ])
    def get(self, request):
        search_number = request.query_params.get('atomic_mass', '')
        elements = Element.objects.filter(atomic_mass__contains=search_number)
        if request.user.is_authenticated:
            decay_information = getDecayInformation(request.user)
        else:
            decay_information = {'decay_elements_count': 0, 
                                 'decay_id': 0}
        serial_data = self.serializer(elements, many = True)
        return Response({'search_number': search_number, 
                         'elements': serial_data.data, 
                         'decay_information': decay_information},
                         status=status.HTTP_200_OK)
    
    @method_permission_classes([IsAuth])
    @swagger_auto_schema(request_body=serializer)
    def post(self, request):
        input_data = self.serializer(data=request.data)
        if input_data.is_valid():
            input_data.save()
            return Response(input_data.data, status=status.HTTP_201_CREATED)
        return Response(input_data.errors, status=status.HTTP_400_BAD_REQUEST)

class elementMethods(APIView):
    serializer = ElementSerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([AllowAny])
    @swagger_auto_schema()
    def get(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        return Response(self.serializer(element).data, status=status.HTTP_200_OK)
    
    @method_permission_classes([IsAuth])
    @swagger_auto_schema(request_body=serializer)
    def post(self, request, element_id):
        decay, is_created = Decay.objects.get_or_create(
            creator = request.user,
            status = 'draft',
        )
        if Element_Decay.objects.filter(element=element_id, decay=decay.decay_id).exists():
            return Response(status=status.HTTP_208_ALREADY_REPORTED)
        else:
            Element_Decay.objects.create(
                decay = Decay.objects.get(decay_id=decay.decay_id),
                element = Element.objects.get(element_id=element_id)
            )
            return Response(status=status.HTTP_200_OK)
    
    @method_permission_classes([IsManager])
    @swagger_auto_schema(request_body=serializer)
    def put(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        changed_element = self.serializer(element, request.data, partial=True)
        if changed_element.is_valid():
            changed_element.save()
            return Response(changed_element.data, status=status.HTTP_200_OK)
        return Response(changed_element.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @method_permission_classes([IsManager])
    @swagger_auto_schema(request_body=serializer)
    def delete(self, request, element_id):
        element = get_object_or_404(Element, pk=element_id)
        if element.status != 'deleted':
            element.status = 'deleted'
            if deleteImg(element.img_url) == 'success':
                element.img_url = ''
                element.save()
                return Response(self.serializer(element).data, status=status.HTTP_204_NO_CONTENT)
            element.save()
            return Response({'s3_img': 'Удаление не удалось'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'element': 'Элемент уже удален'}, status=status.HTTP_208_ALREADY_REPORTED)

@authentication_classes([AuthBySSID])
@permission_classes([IsManager])
@swagger_auto_schema(method='post', request_body=ElementSerializer)
@api_view(['post'])
def elementAddImg(request, element_id):
    element = get_object_or_404(Element, element_id=element_id)
    img = request.FILES.get('img')
    try:
        element.img_url = addImg(img)
        element.save()
        return Response(ElementSerializer(element).data, status=status.HTTP_202_ACCEPTED)
    except:
        return Response({'img': 'Ошибка загрузки'}, status=status.HTTP_400_BAD_REQUEST)


class elementDecayMethods(APIView):
    serializer = ElementDecaySerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([IsManager])
    @swagger_auto_schema(request_body=serializer)
    def delete(self, request, element_id, decay_id):
        element_decay = get_object_or_404(Element_Decay, element=element_id, decay=decay_id)
        element_decay.delete()
        elements_decay = Element_Decay.objects.filter(decay=decay_id)
        return Response(self.serializer(elements_decay, many=True).data, status=status.HTTP_200_OK)
    
    @permission_classes([IsManager])
    @swagger_auto_schema(request_body=serializer)
    def put(self, request, element_id, decay_id):
        element_decay = get_object_or_404(Element_Decay, element=element_id, decay=decay_id)
        changed_element_decay = self.serializer(element_decay, data=request.data, partial=True) 
        if changed_element_decay.is_valid():
            changed_element_decay.save() 
            elements_decay = Element_Decay.objects.filter(decay=decay_id)
            return Response(self.serializer(elements_decay, many=True).data, status=status.HTTP_200_OK)
        return Response(changed_element_decay.errors, status=status.HTTP_400_BAD_REQUEST)

class decaysMethods(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([IsManager])
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'start_date',
            openapi.IN_QUERY,
            description='Начальная дата',
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'end_date',
            openapi.IN_QUERY,
            description='Конечная дата',
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description='Статус (completed/formed/rejected)',
            type=openapi.TYPE_STRING
        )
    ])
    def get(self, request):
        acceptable_statuses = [
            'completed',
            'formed',
            'rejected'
        ]

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        decays = Decay.objects.filter(status__in=acceptable_statuses)

        if start_date and end_date:
            start_date = parse_date(start_date)
            end_date = parse_date(end_date)
            if start_date is None or end_date is None:
                return Response({'error': 'Неправильный формат даты'}, status=status.HTTP_400_BAD_REQUEST)
            decays = decays.filter(date_of_creation__range=(start_date, end_date))

        if status_filter:
            if not status_filter in acceptable_statuses:
                return Response({'error': 'Неправильный статус'}, status=status.HTTP_400_BAD_REQUEST)
            decays = decays.filter(status=status_filter)
        return Response(self.serializer(decays, many=True).data, status=status.HTTP_200_OK)
    
class decayMethods(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([IsAuth])
    def get(self, request):
        decay = get_object_or_404(Decay, creator = request.user, status = 'draft')
        return Response(self.serializer(decay).data, status=status.HTTP_200_OK)
    
    @method_permission_classes([IsAuth])
    @swagger_auto_schema(request_body=serializer)
    def put(self, request):
        decay = get_object_or_404(Decay, creator = request.user, status = 'draft')
        changed_decay = self.serializer(decay, data=request.data, partial=True)
        if changed_decay.is_valid():
            changed_decay.save()
            return Response(changed_decay.data, status=status.HTTP_200_OK)
        return Response(changed_decay.errors, status=status.HTTP_400_BAD_REQUEST)

class formingDecay(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([IsAuth])
    @swagger_auto_schema(request_body=serializer)
    def put(self, request):
        decay = get_object_or_404(Decay, creator = request.user, status = 'draft')
        elements = decay.decay_elements.all()
        if not decay.pass_time is None and decay.pass_time != '':
            for element in elements:
                if element.quantity is None or element.quantity == '':
                    return Response({'quantity': 'Не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
            decay.status = 'formed'
            decay.date_of_formation = timezone.now()
            decay.save()
            return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'pass_time': 'Не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)
    
    @method_permission_classes([IsAuth])
    @swagger_auto_schema(request_body=serializer)
    def delete(self, request):
        decay = get_object_or_404(Decay, creator = request.user, status = 'draft')
        decay.status = 'deleted'
        decay.date_of_formation = timezone.now()
        decay.save()
        return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)

class moderateDecay(APIView):
    serializer = DecaySerializer
    authentication_classes = [AuthBySSID]

    @method_permission_classes([IsManager])
    @swagger_auto_schema(request_body=serializer)
    def put(self, request, decay_id):
        decay = get_object_or_404(Decay, pk=decay_id)
        action = request.data.get('action')
        if decay.status == 'formed':
            if action == 'reject':
                decay.status = 'rejected'
                decay.moderator = request.user
                decay.date_of_finish = timezone.now()
                decay.save()
                return Response(self.serializer(decay).data, status=status.HTTP_200_OK)
            elif action == 'complete':
                elements = decay.decay_elements.all()
                for element in elements:
                    try:
                        element.remaining_quantity = HalfLifeCalculation.half_life_calculation(decay.pass_time, 
                                                                                                element.quantity, 
                                                                                                element.element.period_time)
                    except NameError:
                        element.remaining_quantity = 'Неверный формат входных данных'
                    except ValueError:
                        element.remaining_quantity = 'Неверный формат единиц измерения'
                    element.save()
                decay.moderator = request.user
                decay.status = 'completed'
                decay.date_of_finish = timezone.now()
                decay.save()
                return Response(self.serializer(decay).data, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({'action': 'Неверное действие'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'status': 'Заявка не сформирована'}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    model_class = CustomUser
    authentication_classes = [AuthBySSID]

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = [AllowAny]
        elif self.action in ['list']:
            permission_classes = [IsAuth]

        return super().get_permissions()
    
    def create(self, request):
        if self.model_class.objects.filter(email=request.data['email']).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            self.model_class.objects.create_user(email=serializer.data['email'],
                                     password=serializer.data['password'],
                                     is_superuser=serializer.data['is_superuser'],
                                     is_staff=serializer.data['is_staff'])
            return Response({'status': 'Success'}, status=200)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def list(self, request):
        return Response(self.serializer_class(request.user).data, status=status.HTTP_200_OK)